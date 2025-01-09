# Othello (Reversi) - RPC

# requisitos
- Python 3.12 ou superior
- Pyro5

## Como iniciar
**Observação:** O termo "python" deve ser interpretado como "a palavra-chave para a execução do python no sistema operacional utilizado". Por exemplo, em debian, o termo "python" deve ser interpretado como "python"
### Jogo local (mesmo endereço localhost)
- Abra um terminal e execute o seguinte comando no terminal: python -m Pyro5.nameserver
- Abra um terminal na pasta base do programa (rpc) e execute o seguinte comando no terminal: python server.py
- Abra dois terminais na pasta base do programa (rpc) e execute o seguinte comando em ambos os terminais: python main.py
- O jogo deverá entrar em execução. Para iniciar uma partida, basta que ambos os usuários cliquem no botão "iniciar", no canto inferior direito da tela
- Para fechar o servidor, basta que ambos os usuários fechem o programa. Contudo, o nameserver deve ser manualmente fechado

### Jogo remoto (máquinas diferentes)
- Abra um terminal em cada máquina e execute o seguinte comando em ambos os terminais: python -m Pyro5.nameserver <endereço ip da máquina>
- Na máquina que será o servidor, abra um terminal na pasta base do programa (rpc) e execute o seguinte comando no terminal: python server.py
- Em cada máquina, abra um terminal na pasta base do programa (rpc) e execute o seguinte comando em ambos os terminais: python main.py <endereço ip do servidor>
- O jogo deverá entrar em execução. Para iniciar uma partida, basta que ambos cliquem no botão "iniciar", no canto inferior direito da tela
- Para fechar o servidor, basta que ambos os usuários fechem o programa. Contudo, os nameservers devem ser manualmente fechados

