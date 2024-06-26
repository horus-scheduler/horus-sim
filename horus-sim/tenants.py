import random
import pandas as pd
from loguru import logger

class Tenants:
    def __init__(self, data, worker_dist, num_tenants=100, min_workers=5, max_workers=200):
        self.data = data
        self.num_tenants = num_tenants
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.worker_dist = worker_dist
        self.debug = False

        self.data['tenants'] = {'worker_count': 0,
                                'maps': [{'app_id': None, 'worker_count': None} for _ in range(self.num_tenants)]
                                }

        self.tenants = self.data['tenants']
        self.tenants_maps = self.tenants['maps']

        self._get_tenant_to_worker_count_map()
        
        # for t in range(self.num_tenants):
        #     tenant_maps = self.tenants_maps[t]
        #     tenant_maps['groups_map'] = \
        #         [{'size': None, 'workers': None} for _ in range(tenant_maps['group_count'])]

    def _get_tenant_to_worker_count_map(self):
        if self.worker_dist == 'expon':
            _worker_count = 0
            app_id = 0
            for t in range(self.num_tenants):
                sample = random.random()
                if sample < 0.03:
                    worker_count = random.randint(self.min_workers, self.max_workers)
                else:
                    worker_count = int((random.expovariate(4.05) / 10) * (self.max_workers - self.min_workers)) \
                               % (self.max_workers - self.min_workers) + self.min_workers

                self.tenants_maps[t]['worker_count'] = worker_count
                self.tenants_maps[t]['app_id'] = app_id
                app_id += 1
                _worker_count += worker_count
            self.tenants['worker_count'] = _worker_count
        elif self.worker_dist == 'uniform':
            _worker_count = 0
            app_id = 0
            for t in range(self.num_tenants):
                worker_count = random.randint(self.min_workers, self.max_workers)
                self.tenants_maps[t]['worker_count'] = worker_count
                self.tenants_maps[t]['app_id'] = app_id
                app_id += 1
                _worker_count += worker_count
            self.tenants['worker_count'] = _worker_count
        else:
            raise (Exception("invalid dist parameter for worker allocation"))

        print(pd.Series([self.tenants_maps[t]['worker_count'] for t in range(self.num_tenants)]).describe())
        print("worker Count: %s" % self.tenants['worker_count'])
