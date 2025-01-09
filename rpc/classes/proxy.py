from contextlib import contextmanager

import Pyro5.api

class Proxy(Pyro5.api.Proxy):
    def __init__(self, uri, connected_socket=None):
        super().__init__(uri, connected_socket)

    @contextmanager
    def lending_ownership(self):
        """
        Método que troca a posse do proxy de uma thread para outra (cliente A para B e vice-versa), 
        de modo a permitir que um cliente possa executar um método do outro cliente.
        """
        true_owner = self.__pyroOwnerThread
        try:
#            print('entrou:', self.__pyroOwnerThread)
            self._pyroClaimOwnership()
#            print("obteve:", self.__pyroOwnerThread)
            yield self
        finally:
            self.__pyroOwnerThread = true_owner
#            print('saiu:', self.__pyroOwnerThread)