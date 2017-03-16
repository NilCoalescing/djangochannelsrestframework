def detail_action(**kwargs):
    """
    Used to mark a method on a ResourceBinding that should be routed for detail actions.
    """
    def decorator(func):
        func.action = True
        func.detail = True
        func.kwargs = kwargs
        return func
    return decorator


def list_action(**kwargs):
    """
    Used to mark a method on a ResourceBinding that should be routed for list actions.
    """
    def decorator(func):
        func.action = True
        func.detail = False
        func.kwargs = kwargs
        return func
    return decorator
