"""After install and every migrate: EduCore's custom fields, roles and positions, and upstream read access"""

from educore.access import desk, roles
from educore.admissions import pathways
from educore.setup import custom_fields, permissions, workflows


def after_migrate():
	custom_fields.sync()
	roles.sync()
	permissions.sync()
	workflows.sync()
	desk.sync()
	pathways.ensure_defaults()
