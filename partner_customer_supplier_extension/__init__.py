from . import models

def post_init_hook(env):
    env['res.config.settings']._init_purchase_product_filter()
