data_type_map = {
    'string': str,
    'number': (int, float),
    'boolean': bool,
    'datetime': 'datetime',
    'picture': str
    # Add other data types as needed
}

permissions_table = ['user.create', 'user.read', 'user.edit', 'user.delete',
                     'role.create', 'role.read', 'role.edit', 'role.delete',
                     'permission.create', 'permission.read', 'permission.edit', 'permission.delete',
                     'series.create', 'series.read', 'series.edit', 'series.delete',
                     'product.create', 'product.read', 'product.edit', 'product.delete',
                     'image.read', 'image.create',
                     'log.read',
                     'limit-field.read',
                     'archive.create','archive.delete'
                     ]
