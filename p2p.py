import socket
import json
import os
import threading
import time
import hashlib
import argparse
from datetime import datetime

# ===== CONFIGURAÇÕES =====
TIMEOUT_PADRAO = 3.0
TAMANHO_BUFFER = 65535
INTERVALO_SYNC = 30

class NoP2P:
    def __init__(self, id_no, porta, pasta_sync="tmp"):
        self.id = id_no
        self.porta = porta
        self.pasta = pasta_sync
        self.lista_peers = []
        self.ativo = True
        self.arquivos_locais = {}
        self.sock = None
        self.ultimo_sync = time.time()
        
        # criar pasta se não existir
        if not os.path.exists(self.pasta):
            os.makedirs(self.pasta)
            
        # contadores
        self.enviados = 0
        self.recebidos = 0
        self.bytes_env = 0
        self.bytes_rec = 0
        self.total_syncs = 0
    
    def calc_hash(self, caminho):
        # calcula MD5 do arquivo
        md5 = hashlib.md5()
        try:
            with open(caminho, "rb") as arq:
                while True:
                    dados = arq.read(4096)
                    if not dados:
                        break
                    md5.update(dados)
            return md5.hexdigest()
        except:
            return ""
    
    def escanear_pasta(self):
        # retorna dicionário com arquivos e seus hashes
        resultado = {}
        for nome in os.listdir(self.pasta):
            caminho = os.path.join(self.pasta, nome)
            if os.path.isfile(caminho):
                resultado[nome] = self.calc_hash(caminho)
        return resultado
    
    def iniciar_servidor(self):
        # configura e inicia socket UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.porta))
        self.sock.settimeout(1.0)
        
        print(f"[{self.id}] Servidor rodando na porta {self.porta}")
        
        while self.ativo:
            try:
                dados, endereco = self.sock.recvfrom(TAMANHO_BUFFER)
                threading.Thread(target=self.processar_msg, args=(dados, endereco)).start()
            except socket.timeout:
                continue
            except Exception as erro:
                print(f"[{self.id}] Erro no servidor: {erro}")
    
    def processar_msg(self, dados, endereco):
        # processa mensagens recebidas
        try:
            msg = json.loads(dados.decode('utf-8'))
            tipo = msg.get('type')
            
            if tipo == 'LIST_FILES':
                self.responder_lista(endereco)
            elif tipo == 'GET_FILE':
                self.enviar_arquivo(msg, endereco)
            elif tipo == 'DELETE_FILE':
                self.deletar_arquivo(msg, endereco)
            elif tipo == 'FILE_ANNOUNCE':
                pass  # só recebe o anúncio
            elif tipo == 'PING':
                self.responder_ping(endereco)
            elif tipo == 'JOIN':
                self.aceitar_novo_no(msg, endereco)
                
        except Exception as erro:
            print(f"[{self.id}] Erro processando: {erro}")
    
    def responder_lista(self, endereco):
        self.arquivos_locais = self.escanear_pasta()
        resposta = {
            'type': 'FILE_LIST',
            'node_id': self.id,
            'files': self.arquivos_locais
        }
        self.mandar_msg(resposta, endereco)
    
    def enviar_arquivo(self, msg, endereco):
        nome = msg.get('filename')
        caminho = os.path.join(self.pasta, nome)
        
        if not os.path.exists(caminho):
            return
        
        try:
            with open(caminho, 'rb') as f:
                conteudo = f.read()
            
            resposta = {
                'type': 'FILE_DATA',
                'filename': nome,
                'content': conteudo.hex(),
                'hash': self.calc_hash(caminho)
            }
            
            self.mandar_msg(resposta, endereco)
            self.enviados += 1
            self.bytes_env += len(conteudo)
            print(f"[{self.id}] '{nome}' enviado para {endereco}")
            
        except Exception as erro:
            print(f"[{self.id}] Erro enviando: {erro}")
    
    def deletar_arquivo(self, msg, endereco):
        nome = msg.get('filename')
        caminho = os.path.join(self.pasta, nome)
        
        if os.path.exists(caminho):
            try:
                os.remove(caminho)
                print(f"[{self.id}] '{nome}' removido")
                resp = {'type': 'DELETE_ACK', 'filename': nome}
                self.mandar_msg(resp, endereco)
            except Exception as erro:
                print(f"[{self.id}] Erro deletando: {erro}")
    
    def responder_ping(self, endereco):
        resp = {'type': 'PONG', 'node_id': self.id}
        self.mandar_msg(resp, endereco)
    
    def aceitar_novo_no(self, msg, endereco):
        novo_id = msg.get('node_id')
        nova_porta = msg.get('port')
        
        peer = (endereco[0], nova_porta)
        if peer not in self.lista_peers and nova_porta != self.porta:
            self.lista_peers.append(peer)
            print(f"[{self.id}] Novo nó '{novo_id}' conectado")
        
        resp = {
            'type': 'JOIN_ACK',
            'peers': [(p[0], p[1]) for p in self.lista_peers if p != peer]
        }
        self.mandar_msg(resp, endereco)
    
    def mandar_msg(self, msg, endereco):
        try:
            dados = json.dumps(msg).encode('utf-8')
            temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp.sendto(dados, endereco)
            temp.close()
        except Exception as erro:
            print(f"[{self.id}] Erro mandando msg: {erro}")
    
    def pedir_arquivo(self, nome, peer):
        # solicita arquivo de um peer específico
        pedido = {
            'type': 'GET_FILE',
            'filename': nome,
            'node_id': self.id
        }
        
        try:
            temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp.settimeout(5.0)
            temp.bind(('', 0))
            
            temp.sendto(json.dumps(pedido).encode('utf-8'), peer)
            
            dados, _ = temp.recvfrom(TAMANHO_BUFFER)
            resp = json.loads(dados.decode('utf-8'))
            
            if resp.get('type') == 'FILE_DATA':
                conteudo = bytes.fromhex(resp['content'])
                caminho = os.path.join(self.pasta, nome)
                
                with open(caminho, 'wb') as f:
                    f.write(conteudo)
                
                self.recebidos += 1
                self.bytes_rec += len(conteudo)
                print(f"[{self.id}] '{nome}' baixado de {peer}")
                temp.close()
                return True
                
        except socket.timeout:
            print(f"[{self.id}] Timeout ao pedir '{nome}'")
        except Exception as erro:
            print(f"[{self.id}] Erro baixando: {erro}")
        
        return False
    
    def propagar_delete(self, nome):
        # avisa todos os peers sobre deleção
        msg = {
            'type': 'DELETE_FILE',
            'filename': nome,
            'node_id': self.id
        }
        
        for peer in self.lista_peers:
            self.mandar_msg(msg, peer)
    
    def sincronizar(self):
        print(f"\n[{self.id}] Sincronizando...")
        self.total_syncs += 1
        
        self.arquivos_locais = self.escanear_pasta()
        
        # pegar lista de arquivos de cada peer
        arquivos_rede = {}
        for peer in self.lista_peers:
            pedido = {'type': 'LIST_FILES', 'node_id': self.id}
            
            try:
                temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                temp.settimeout(TIMEOUT_PADRAO)
                temp.sendto(json.dumps(pedido).encode('utf-8'), peer)
                
                dados, _ = temp.recvfrom(TAMANHO_BUFFER)
                resp = json.loads(dados.decode('utf-8'))
                
                if resp.get('type') == 'FILE_LIST':
                    arquivos_peer = resp.get('files', {})
                    for nome_arq, hash_arq in arquivos_peer.items():
                        if nome_arq not in arquivos_rede:
                            arquivos_rede[nome_arq] = []
                        arquivos_rede[nome_arq].append((peer, hash_arq))
                
                temp.close()
                
            except Exception as erro:
                print(f"[{self.id}] Erro listando de {peer}: {erro}")
        
        # baixar arquivos faltantes
        for nome, fontes in arquivos_rede.items():
            if nome not in self.arquivos_locais:
                for peer, _ in fontes:
                    if self.pedir_arquivo(nome, peer):
                        break
        
        # anunciar arquivos locais
        if self.arquivos_locais:
            anuncio = {
                'type': 'FILE_ANNOUNCE',
                'node_id': self.id,
                'files': self.arquivos_locais
            }
            for peer in self.lista_peers:
                self.mandar_msg(anuncio, peer)
        
        print(f"[{self.id}] Sincronização OK")
        self.ultimo_sync = time.time()
    
    def add_peer(self, host, porta):
        peer = (host, porta)
        if peer not in self.lista_peers and porta != self.porta:
            self.lista_peers.append(peer)
            print(f"[{self.id}] Peer {host}:{porta} adicionado")
    
    def entrar_rede(self, bootstrap):
        msg = {
            'type': 'JOIN',
            'node_id': self.id,
            'port': self.porta
        }
        
        try:
            temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp.settimeout(5.0)
            temp.sendto(json.dumps(msg).encode('utf-8'), bootstrap)
            
            dados, _ = temp.recvfrom(TAMANHO_BUFFER)
            resp = json.loads(dados.decode('utf-8'))
            
            if resp.get('type') == 'JOIN_ACK':
                peers = resp.get('peers', [])
                for h, p in peers:
                    self.add_peer(h, p)
                
                print(f"[{self.id}] Conectado na rede!")
                temp.close()
                return True
                
        except Exception as erro:
            print(f"[{self.id}] Erro conectando: {erro}")
        
        return False
    
    def monitorar_pasta(self):
        # detecta mudanças na pasta
        ultimos = set()
        
        while self.ativo:
            try:
                atuais = set(os.listdir(self.pasta))
                
                novos = atuais - ultimos
                if novos:
                    for nome in novos:
                        print(f"[{self.id}] Novo: {nome}")
                    self.sincronizar()
                
                deletados = ultimos - atuais
                if deletados:
                    for nome in deletados:
                        print(f"[{self.id}] Removido: {nome}")
                        self.propagar_delete(nome)
                
                ultimos = atuais
                time.sleep(2)
                
            except Exception as erro:
                print(f"[{self.id}] Erro monitorando: {erro}")
    
    def sync_automatico(self):
        while self.ativo:
            time.sleep(INTERVALO_SYNC)
            if self.ativo:
                self.sincronizar()
    
    def listar_arquivos(self):
        self.arquivos_locais = self.escanear_pasta()
        
        print(f"\n{'='*50}")
        print(f"ARQUIVOS DO NÓ '{self.id}'")
        print(f"{'='*50}")
        
        print("\nLocais:")
        if self.arquivos_locais:
            for nome, hash_arq in self.arquivos_locais.items():
                caminho = os.path.join(self.pasta, nome)
                tamanho = os.path.getsize(caminho)
                print(f"  - {nome} ({tamanho} bytes) Hash: {hash_arq[:8]}...")
        else:
            print("  Nenhum")
        
        print("\nNa Rede:")
        rede = {}
        for peer in self.lista_peers:
            pedido = {'type': 'LIST_FILES', 'node_id': self.id}
            try:
                temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                temp.settimeout(2.0)
                temp.sendto(json.dumps(pedido).encode('utf-8'), peer)
                
                dados, _ = temp.recvfrom(TAMANHO_BUFFER)
                resp = json.loads(dados.decode('utf-8'))
                
                if resp.get('type') == 'FILE_LIST':
                    for nome in resp.get('files', {}):
                        if nome not in rede:
                            rede[nome] = []
                        rede[nome].append(f"{peer[0]}:{peer[1]}")
                
                temp.close()
            except:
                pass
        
        if rede:
            for nome, locais in rede.items():
                tem = "✓" if nome in self.arquivos_locais else "✗"
                print(f"  {tem} {nome} em: {', '.join(locais)}")
        else:
            print("  Nenhum")
        
        print(f"{'='*50}\n")
    
    def mostrar_stats(self):
        print(f"\n{'='*50}")
        print(f"ESTATÍSTICAS '{self.id}'")
        print(f"{'='*50}")
        print(f"Enviados: {self.enviados}")
        print(f"Recebidos: {self.recebidos}")
        print(f"Bytes enviados: {self.bytes_env:,}")
        print(f"Bytes recebidos: {self.bytes_rec:,}")
        print(f"Sincronizações: {self.total_syncs}")
        print(f"Peers: {len(self.lista_peers)}")
        print(f"Último sync: {datetime.fromtimestamp(self.ultimo_sync).strftime('%H:%M:%S')}")
        print(f"{'='*50}\n")
    
    def menu(self):
        print(f"\n{'='*50}")
        print(f"Sistema P2P - '{self.id}'")
        print(f"{'='*50}")
        print("1 - Ver arquivos")
        print("2 - Sincronizar")
        print("3 - Adicionar peer")
        print("4 - Estatísticas")
        print("5 - Ver peers")
        print("6 - Adicionar arquivo")
        print("7 - Remover arquivo")
        print("8 - Entrar em rede")
        print("9 - Sair")
        print(f"{'='*50}\n")
        
        while self.ativo:
            try:
                cmd = input(f"[{self.id}]> ").strip()
                
                if cmd == '1':
                    self.listar_arquivos()
                
                elif cmd == '2':
                    self.sincronizar()
                
                elif cmd == '3':
                    h = input("Host: ").strip()
                    p = int(input("Porta: ").strip())
                    self.add_peer(h, p)
                
                elif cmd == '4':
                    self.mostrar_stats()
                
                elif cmd == '5':
                    print("\nPeers:")
                    for i, p in enumerate(self.lista_peers, 1):
                        print(f"  {i}. {p[0]}:{p[1]}")
                    if not self.lista_peers:
                        print("  Nenhum")
                
                elif cmd == '6':
                    caminho = input("Arquivo: ").strip()
                    if os.path.exists(caminho):
                        nome = os.path.basename(caminho)
                        dest = os.path.join(self.pasta, nome)
                        with open(caminho, 'rb') as f1, open(dest, 'wb') as f2:
                            f2.write(f1.read())
                        print(f"'{nome}' adicionado")
                    else:
                        print("Não encontrado")
                
                elif cmd == '7':
                    nome = input("Nome: ").strip()
                    caminho = os.path.join(self.pasta, nome)
                    if os.path.exists(caminho):
                        os.remove(caminho)
                        self.propagar_delete(nome)
                        print(f"'{nome}' removido")
                    else:
                        print("Não encontrado")
                
                elif cmd == '8':
                    h = input("Host bootstrap: ").strip()
                    p = int(input("Porta bootstrap: ").strip())
                    if self.entrar_rede((h, p)):
                        print("Conectado!")
                    else:
                        print("Falhou")
                
                elif cmd == '9':
                    self.parar()
                    break
                
                else:
                    print("Comando inválido")
                    
            except KeyboardInterrupt:
                print("\n\nSaindo...")
                self.parar()
                break
            except Exception as erro:
                print(f"Erro: {erro}")
    
    def parar(self):
        self.ativo = False
        if self.sock:
            self.sock.close()
        print(f"[{self.id}] Encerrado")
    
    def executar(self):
        # inicia threads
        t1 = threading.Thread(target=self.iniciar_servidor)
        t1.daemon = True
        t1.start()
        
        t2 = threading.Thread(target=self.monitorar_pasta)
        t2.daemon = True
        t2.start()
        
        t3 = threading.Thread(target=self.sync_automatico)
        t3.daemon = True
        t3.start()
        
        time.sleep(1)
        self.menu()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sistema P2P')
    parser.add_argument('--id', type=str, required=True, help='ID do nó')
    parser.add_argument('--port', type=int, required=True, help='Porta UDP')
    parser.add_argument('--dir', type=str, default='tmp', help='Pasta sync')
    parser.add_argument('--peer', type=str, help='Peer inicial (host:porta)')
    
    args = parser.parse_args()
    
    no = NoP2P(args.id, args.port, args.dir)
    
    if args.peer:
        try:
            h, p = args.peer.split(':')
            no.add_peer(h, int(p))
        except:
            print("Formato inválido. Use: host:porta")
    
    try:
        no.executar()
    except KeyboardInterrupt:
        print("\nSaindo...")
        no.parar()