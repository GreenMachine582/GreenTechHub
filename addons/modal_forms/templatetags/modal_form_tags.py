from django import template
register = template.Library()

@register.inclusion_tag("modal_forms/confirm_modal.html")
def confirm_delete_modal(action_url, modal_id="confirmDeleteModal",
                         title="Confirm Delete",
                         message="Are you sure you want to delete this record? This action cannot be undone.",
                         confirm_label="Yes, delete",
                         header_class="bg-danger text-white",
                         confirm_class="btn-danger",
                         icon="fas fa-bomb"):
    return {
        "action_url": action_url,
        "modal_id": modal_id,
        "title": title,
        "message": message,
        "confirm_label": confirm_label,
        "header_class": header_class,
        "confirm_class": confirm_class,
        "icon": icon,
    }
