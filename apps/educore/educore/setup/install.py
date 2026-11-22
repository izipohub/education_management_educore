"""After install and every migrate: EduCore's custom fields, roles and positions, and upstream read access"""

from educore.access import roles
from educore.setup import custom_fields, permissions, workflows


def after_migrate():
	custom_fields.sync()
	roles.sync()
	permissions.sync()
	workflows.sync()
