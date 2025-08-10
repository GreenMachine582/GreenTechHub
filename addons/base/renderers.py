
from django_bootstrap5.renderers import FieldRenderer as BaseFieldRenderer


class FieldRenderer(BaseFieldRenderer):

    def __init__(self, field, **kwargs):
        """
        Custom FieldRenderer to handle checkbox styles.
        """
        if (widget := field.field.widget).input_type == "checkbox":
            if style := widget.attrs.get("checkbox_style"):
                kwargs["checkbox_style"] = style
        super().__init__(field, **kwargs)
