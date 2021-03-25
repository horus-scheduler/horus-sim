import os
import random

from loguru import logger

class Placement:
    def __init__(self, data, num_pods=4, num_leafs_per_pod=4, num_hosts_per_leaf=10,
                 max_workers_per_host=10, dist='colocate-uniform'):
        self.data = data
        self.num_pods = num_pods
        self.num_leafs_per_pod = num_leafs_per_pod
        self.num_hosts_per_leaf = num_hosts_per_leaf
        self.num_tenants = len(data['tenants']['maps'])
        self.max_workers_per_host = max_workers_per_host
        self.dist = dist

        self.tenants = self.data['tenants']
        self.tenants_maps = self.tenants['maps']

        for t in range(self.num_tenants):
            tenant_maps = self.tenants_maps[t]
            tenant_maps['worker_to_host_map'] = [
                None for _ in range(tenant_maps['worker_count'])]

        self._get_tenant_workers_to_host_map()

    def _colocate_pods__uniform_hosts(self):
        available_pods = list(range(self.num_pods))
        available_hosts_per_pod = [None] * self.num_pods
        available_hosts_count_per_pod = [None] * self.num_pods

        for p in range(self.num_pods):
            # Khaled: I added "+ 1" to match the numbering conventions between
            # code of dataset generation and our FatTree implementation
            available_hosts_per_pod[p] = [(((p * self.num_leafs_per_pod) + l) * self.num_hosts_per_leaf) + h
                                          for l in range(self.num_leafs_per_pod)
                                          for h in range(self.num_hosts_per_leaf)]

            available_hosts_count_per_pod[p] = [
                0] * self.num_leafs_per_pod * self.num_hosts_per_leaf

        tenants_maps = self.tenants_maps
        for t in range(self.num_tenants):
            tenant_maps = tenants_maps[t]
            worker_to_host_map = tenant_maps['worker_to_host_map']
            worker_index = 0
            worker_count = tenant_maps['worker_count']

            while worker_count > 0:
                # print('>>>>>', available_pods)
                selected_pod = random.sample(available_pods, 1)[0]
                selected_pod_index = available_pods.index(selected_pod)
                selected_hosts = available_hosts_per_pod[selected_pod_index]
                selected_hosts_count = available_hosts_count_per_pod[selected_pod_index]

                sampled_hosts = random.sample(
                    selected_hosts, min(len(selected_hosts), worker_count))
                for h in sampled_hosts:
                    worker_to_host_map[worker_index] = h
                    selected_hosts_count[selected_hosts.index(h)] += 1
                    worker_index += 1
                worker_count -= len(sampled_hosts)

                removed_hosts_indexes = [i for i, c in enumerate(
                    selected_hosts_count) if c == self.max_workers_per_host]
                for i in sorted(removed_hosts_indexes, reverse=True):
                    del selected_hosts[i]
                    del selected_hosts_count[i]

                if len(selected_hosts) == 0:
                    del available_pods[selected_pod_index]
                    del available_hosts_per_pod[selected_pod_index]
                    del available_hosts_count_per_pod[selected_pod_index]

    def _colocate_pods__colocate_leafs__uniform_hosts(self):
        available_pods = list(range(self.num_pods))
        available_leafs_per_pod = [None] * self.num_pods
        available_hosts_per_leaf_per_pod = [None] * self.num_pods
        available_hosts_count_per_leaf_per_pod = [None] * self.num_pods

        for p in range(self.num_pods):
            available_leafs_per_pod[p] = [
                (p * self.num_leafs_per_pod) + l for l in range(self.num_leafs_per_pod)]
            available_hosts_per_leaf_per_pod[p] = [
                None] * self.num_leafs_per_pod
            available_hosts_count_per_leaf_per_pod[p] = [
                None] * self.num_leafs_per_pod

            available_leafs = available_leafs_per_pod[p]
            available_hosts_per_leaf = available_hosts_per_leaf_per_pod[p]
            available_hosts_count_per_leaf = available_hosts_count_per_leaf_per_pod[p]
            for l in range(self.num_leafs_per_pod):
                available_hosts_per_leaf[l] = [(available_leafs[l] * self.num_hosts_per_leaf) + h 
                                               for h in range(self.num_hosts_per_leaf)]
                # print('>>', available_hosts_per_leaf[l])
                available_hosts_count_per_leaf[l] = [
                    0] * self.num_hosts_per_leaf

        tenants_maps = self.tenants_maps
        for t in range(self.num_tenants):
            tenant_maps = tenants_maps[t]
            worker_to_host_map = tenant_maps['worker_to_host_map']
            worker_index = 0
            worker_count = tenant_maps['worker_count']

            while worker_count > 0:
                selected_pod = random.sample(available_pods, 1)[0]
                selected_pod_index = available_pods.index(selected_pod)
                selected_leafs = available_leafs_per_pod[selected_pod_index]
                selected_hosts_per_leaf = available_hosts_per_leaf_per_pod[selected_pod_index]
                selected_hosts_count_per_leaf = available_hosts_count_per_leaf_per_pod[
                    selected_pod_index]

                while worker_count > 0 and len(selected_leafs) > 0:
                    selected_leaf = random.sample(selected_leafs, 1)[0]
                    selected_leaf_index = selected_leafs.index(selected_leaf)
                    selected_hosts = selected_hosts_per_leaf[selected_leaf_index]
                    selected_hosts_count = selected_hosts_count_per_leaf[selected_leaf_index]

                    sampled_hosts = random.sample(
                        selected_hosts, min(len(selected_hosts), worker_count))
                    for h in sampled_hosts:
                        worker_to_host_map[worker_index] = h
                        selected_hosts_count[selected_hosts.index(h)] += 1
                        worker_index += 1
                    worker_count -= len(sampled_hosts)

                    removed_hosts_indexes = [i for i, c in enumerate(selected_hosts_count)
                                             if c == self.max_workers_per_host]
                    for i in sorted(removed_hosts_indexes, reverse=True):
                        del selected_hosts[i]
                        del selected_hosts_count[i]

                    if len(selected_hosts) == 0:
                        del selected_leafs[selected_leaf_index]
                        del selected_hosts_per_leaf[selected_leaf_index]
                        del selected_hosts_count_per_leaf[selected_leaf_index]

                if len(selected_leafs) == 0:
                    del available_pods[selected_pod_index]
                    del available_leafs_per_pod[selected_pod_index]
                    del available_hosts_per_leaf_per_pod[selected_pod_index]
                    del available_hosts_count_per_leaf_per_pod[selected_pod_index]

    def _get_tenant_workers_to_host_map(self):
        if self.dist == 'colocate-uniform':
            self._colocate_pods__uniform_hosts()
        elif self.dist == 'colocate-colocate-uniform':
            self._colocate_pods__colocate_leafs__uniform_hosts()
        else:
            raise(Exception('invalid dist parameter for worker to host allocation'))
