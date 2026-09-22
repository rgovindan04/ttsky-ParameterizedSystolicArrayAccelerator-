"""Shared, deliberately small architecture sweep. No measured timing implied."""
CONFIGS = {
    'tiny': dict(DATA_W=4, ACC_W=12, ROWS=1, COLS=1, K=2),
    'small': dict(DATA_W=4, ACC_W=16, ROWS=2, COLS=2, K=2),
    'default': dict(DATA_W=8, ACC_W=24, ROWS=2, COLS=2, K=2),
    'wide_acc': dict(DATA_W=8, ACC_W=32, ROWS=2, COLS=2, K=2),
    'rectangular': dict(DATA_W=8, ACC_W=24, ROWS=2, COLS=3, K=4),
    'tall': dict(DATA_W=4, ACC_W=12, ROWS=3, COLS=1, K=3),
    'byte_padding': dict(DATA_W=9, ACC_W=20, ROWS=1, COLS=2, K=3),
    'overflow': dict(DATA_W=8, ACC_W=16, ROWS=2, COLS=2, K=5),
    'single': dict(DATA_W=2, ACC_W=4, ROWS=1, COLS=1, K=1),
    'wide_data': dict(DATA_W=16, ACC_W=32, ROWS=1, COLS=1, K=2),
}


def validate(config):
    if any(not isinstance(v, int) or v < 1 for v in config.values()):
        raise ValueError('All parameters must be positive integers')
    if config['ACC_W'] < 2*config['DATA_W']:
        raise ValueError('ACC_W must be at least 2*DATA_W')
