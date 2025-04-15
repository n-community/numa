from google.appengine.ext import db
from google.appengine.api import datastore_errors

class SetProperty(db.Property):
  """A property that stores a set of things.

  This is a parameterized property; the parameter must be a valid
  non-list data type, and all items must conform to this type.
  """

  def __init__(self, item_type, verbose_name=None, default=None, **kwds):
    """Construct SetProperty.

    Args:
      item_type: Type for the set items; must be one of the allowed property
        types.
      verbose_name: Optional verbose name.
      default: Optional default value; if omitted, an empty list is used.
      **kwds: Optional additional keyword arguments, passed to base class.

    Note that the only permissible value for 'required' is True.
    """
    if not isinstance(item_type, type):
      raise TypeError('Item type should be a type object')
    if item_type not in db._ALLOWED_PROPERTY_TYPES:
      raise ValueError('Item type %s is not acceptable' % item_type.__name__)
    if issubclass(item_type, (db.Blob, db.Text)):
      self._require_parameter(kwds, 'indexed', False)
      kwds['indexed'] = True
    self._require_parameter(kwds, 'required', True)
    if default is None:
      default = set()
    self.item_type = item_type
    super(SetProperty, self).__init__(verbose_name,
                                      default=default,
                                      **kwds)

  def validate(self, value):
    """Validate set.

    Returns:
      A valid value.

    Raises:
      BadValueError if property is not a set whose items are instances of
      the item_type given to the constructor.
    """
    value = super(SetProperty, self).validate(value)
    if value is not None:
      if not isinstance(value, set):
        raise db.BadValueError('Property %s must be a set' % self.name)

      value = self.validate_set_contents(value)
    return value

  def validate_set_contents(self, value):
    """Validates that all items in the set are of the correct type.

    Returns:
      The validated set.

    Raises:
      BadValueError if the set has items are not instances of the
      item_type given to the constructor.
    """
    for item in value:
      if not isinstance(item, self.item_type):
        raise db.BadValueError(
            'Items in the %s set must all be %s instances' %
            (self.name, self.item_type.__name__))
    return value

  def empty(self, value):
    """Is list property empty.

    [] is not an empty value.

    Returns:
      True if value is None, else false.
    """
    return value is None

  data_type = list

  def default_value(self):
    """Default value for set.

    Because the property supplied to 'default' is a static value,
    that value must be shallow copied to prevent all fields with
    default values from sharing the same instance.

    Returns:
      Copy of the default value.
    """
    return set(super(SetProperty, self).default_value())

  def get_value_for_datastore(self, model_instance):
    """Get value from property to send to datastore.

    Returns:
      validated list appropriate to save in the datastore.
    """
    value = self.validate_set_contents(
        super(SetProperty, self).get_value_for_datastore(model_instance))
    if self.validator:
      self.validator(value)
    return list(value)

  def make_value_from_datastore(self, value):
    return set(value)
