def get_or_none(model, *args, **kwargs):
    """
        get a model or return None if not found
        pass in a model with filters
    """
    try:
        return model.objects.get(*args, **kwargs)
    except (model.DoesNotExist, ValueError, Exception):
        return None