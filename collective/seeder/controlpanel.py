from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper

from collective.seeder.interfaces import ISeederSettings
from plone.z3cform import layout

class SeederControlPanelForm(RegistryEditForm):
    schema = ISeederSettings

SeederControlPanelView = layout.wrap_form(SeederControlPanelForm, ControlPanelFormWrapper)

