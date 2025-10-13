class BaseRouter:

    def get_backend_name(self, recipient, **kwargs):
        """
        Method should return name of the backend specified in PYMESS_*_BACKEND_ROUTER setting option
        """
        raise NotImplementedError


class DefaultBackendRouter(BaseRouter):

    def get_backend_name(self, recipient, **kwargs):
        return None
