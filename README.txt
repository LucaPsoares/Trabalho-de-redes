===============================================================================
                          EXECUÇÃO BÁSICA
================================================================================

SINTAXE:
  python p2p.py --id <ID_DO_NO> --port <PORTA> [OPÇÕES]

PARÂMETROS OBRIGATÓRIOS:
  --id      ID único do nó (ex: NodeA, Node1, Servidor)
  --port    Porta UDP para comunicação (ex: 5000)

PARÂMETROS OPCIONAIS:
  --dir     Diretório de sincronização (padrão: tmp)
  --peer    Peer inicial para conectar (formato: host:porta)

================================================================================
                       EXEMPLOS DE USO
================================================================================

--- EXEMPLO 1: Nó Individual ---

Windows:
  python p2p.py --id NodeA --port 5000

Linux/Mac:
  python3 p2p.py --id NodeA --port 5000


--- EXEMPLO 2: Rede com 2 Nós (Mesma Máquina) ---

Terminal 1 (Nó Principal):
  python p2p.py --id NodeA --port 5000

Terminal 2 (Conecta ao primeiro):
  python p2p.py --id NodeB --port 5001 --peer localhost:5000


--- EXEMPLO 3: Rede com 3 Nós ---

Terminal 1:
  python p2p.py --id NodeA --port 5000

Terminal 2:
  python p2p.py --id NodeB --port 5001 --peer localhost:5000

Terminal 3:
  python p2p.py --id NodeC --port 5002 --peer localhost:5000


--- EXEMPLO 4: Diretório Personalizado ---

  python p2p.py --id NodeA --port 5000 --dir meus_arquivos


--- EXEMPLO 5: Conectar em Máquina Remota ---

  python p2p.py --id NodeRemoto --port 5001 --peer 192.168.1.100:5000

  (Substitua 192.168.1.100 pelo IP real da máquina remota)

================================================================================
                        MENU INTERATIVO
================================================================================

Após iniciar o nó, você terá acesso ao menu:

1 - Ver arquivos
    Lista arquivos locais e disponíveis na rede

2 - Sincronizar
    Força sincronização imediata com todos os peers

3 - Adicionar peer
    Adiciona manualmente um novo peer à rede

4 - Estatísticas
    Exibe informações sobre transferências e performance

5 - Ver peers
    Lista todos os peers conectados

6 - Adicionar arquivo
    Copia um arquivo externo para o sistema de sincronização

7 - Remover arquivo
    Remove um arquivo local e propaga a remoção

8 - Entrar em rede
    Conecta dinamicamente a uma rede existente

9 - Sair
    Encerra o nó

================================================================================
                    CONFIGURAÇÃO DE REDE
================================================================================

--- MODO LOCAL (Mesma Máquina) ---

Use 'localhost' ou '127.0.0.1' como host e portas diferentes:
  NodeA: porta 5000
  NodeB: porta 5001
  NodeC: porta 5002


--- MODO LAN (Rede Local) ---

1. Descubra o IP da máquina servidor:
   Windows:  ipconfig
   Linux:    ip addr ou ifconfig

2. Configure firewall para permitir portas UDP

3. No cliente, use o IP descoberto:
   python p2p.py --id Cliente --port 5001 --peer 192.168.1.X:5000


--- WINDOWS + VIRTUALBOX (Linux) ---

1. Configure VirtualBox em modo "Bridge"

2. No Windows (servidor):
   - Libere porta no firewall
   - Execute: python p2p.py --id WinNode --port 5000

3. No Linux (cliente):
   - Use IP do Windows
   - Execute: python3 p2p.py --id LinuxNode --port 5001 --peer IP_WINDOWS:5000


================================================================================
                          FUNCIONAMENTO
================================================================================

SINCRONIZAÇÃO AUTOMÁTICA:
- O sistema sincroniza automaticamente a cada 30 segundos
- Detecta novos arquivos na pasta 'tmp' em tempo real
- Propaga deleções para todos os peers

DETECÇÃO DE ARQUIVOS:
- Monitora a pasta de sincronização continuamente
- Calcula hash MD5 para verificar integridade
- Sincroniza automaticamente quando detecta mudanças

COMUNICAÇÃO:
- Usa protocolo UDP (sem conexão persistente)
- Mensagens em formato JSON
- Timeout configurado para 3 segundos

ARQUIVOS:
- Armazenados na pasta 'tmp' (ou especificada em --dir)
- Sincronizados automaticamente entre todos os peers
- Hash MD5 garante integridade

================================================================================
                        ESTRUTURA DE PASTAS
================================================================================

trabalhoRedes/
├── p2p.py              # Código principal
├── README.txt          # Este arquivo
└── tmp/                # Pasta de sincronização (criada automaticamente)
  

================================================================================
                       TESTANDO O SISTEMA
================================================================================

--- TESTE RÁPIDO (1 minuto) ---

1. Abra 2 terminais

2. Terminal 1:
   python p2p.py --id NodeA --port 5000

3. Terminal 2:
   python p2p.py --id NodeB --port 5001 --peer localhost:5000

4. No NodeA, digite: 6
   Adicione um arquivo qualquer (EXEMPLO: test1.txt ou test2.txt)

5. No NodeB, digite: 2
   Deve baixar o arquivo do NodeA

6. No NodeB, digite: 1
   Deve listar o arquivo sincronizado


--- TESTE COMPLETO ---

1. Inicie 3 nós (portas 5000, 5001, 5002)

2. Adicione arquivo no Node1

3. Verifique sincronização nos outros nós (comando 1)

4. Delete arquivo no Node2 (comando 7)

5. Verifique se foi removido de todos

6. Veja estatísticas (comando 4)