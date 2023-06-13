import hashlib
import json
import requests
import socketio
from flask_cors import CORS





from threading import Thread
# import time
from time import time
from time import sleep
from uuid import uuid4
from urllib.parse import urlparse
from flask import Flask, jsonify, request
import multiprocessing as mp


sio = socketio.Client()


class Blockchain(object):

    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        self.nodes_in_validation = []

    
        self.deleted_nodes = [{
            'deleted_nodes': [],
            'senders': set(),
        }]
        self.added_nodes = [{
            'added_nodes': [],
            'senders': set(),
        }]
        self.transaction_resolver = []
        self.mining_list = []
        self.mining_resolver = []


        self.host='0.0.0.0'
        self.port=1002

     

        # Створення блоку генези
        self.new_block(previous_hash=1, proof=100)
        self.node_register()


    def transaction_validator(self, sender, recipient, amount):
        nodes = self.nodes
        nodes_in_validation = self.nodes_in_validation
        current_transactions = self.current_transactions
        chain = self.chain
        transaction_valid_status = True 
        node_is_valid = True
        deactiveNode = set()   
        self_node_adress = f'{self.host}:{self.port}'
        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        }
 




        for node_in_validation in nodes_in_validation:                           #чи міститься нода з такою транзакцією в нодах для валідації
            if ((self_node_adress in node_in_validation["node_id"]) and (transaction == node_in_validation["transaction"])) == True: node_is_valid = False
        if node_is_valid:
            print("dodaemo nodu")
            self.nodes_in_validation.append({                       #якщо не міститься тоді додаємо в список нод у валідації
                'node_id': self_node_adress,
                'transaction': transaction,
                'status': False,   #bool
                'timestamp': time()
            })


        if transaction_valid_status:
            for block in chain:                                                         #чи міститься транзакція в ланцюгу
                for transactions in block["transactions"]:
                    if transactions["sender"] == transaction["sender"]: transaction_valid_status = False


        if transaction_valid_status:                                                #шукаємо нашу провалідувану транзакцію та змінюємо її статус
            for node_in_validation in nodes_in_validation:        
                if ((self_node_adress in node_in_validation["node_id"]) and (transaction == node_in_validation["transaction"])) == True: 
                    node_in_validation["status"] = True


        print(nodes)

        for node in nodes:

            not_include = True
            if node_is_valid:
                for node_in_validation in nodes_in_validation:         
                    if ((node == node_in_validation["node_id"]) and (transaction == node_in_validation["transaction"])) == True: not_include = False
                print(not_include,  node, 'розсилка валідованої ноди')            
                if not_include:
                    if node_is_valid:                                        #якщо транзакція була додана 
                        for node_in_validation in nodes_in_validation:                        #шукаємо цю транзакцію в списку валідованих транзакцій       
                            if ((self_node_adress in node_in_validation["node_id"]) and (transaction == node_in_validation["transaction"])) == True:
                                try: 
                                    requests.post(f'http://{node}/transactions/addtovalidation', json = {
                                        "node_in_validation": node_in_validation,
                                        "sender": self_node_adress
                                    })
                                except: deactiveNode.add(node)

        print("nodes:", nodes)
        
        for node in nodes:

            not_include = True
            for node_in_validation in self.nodes_in_validation:         
                if ((node in node_in_validation["node_id"]) and (transaction == node_in_validation["transaction"])) == True: not_include = False
            print("not_include:",not_include, "node:", node)

            if not_include and node != self_node_adress:
                try:
                        response = requests.post(f'http://{node}/transactions/new', json = {
                            "transaction": transaction,
                            "sender": self_node_adress
                        })
                        valid_status = response.json()
                        print(type(valid_status) == bool)
                        if (type(valid_status) == bool):
                            print("ajsdjadaj")
                            print(valid_status)
                            not_include = True
                            for node_in_validation in nodes_in_validation:         #друга перевірка зроблена що б запобігти ситуації коли під час виконання цього блоку коду прилітає провалідована транзакція, із за цього можливе додаваня в node_in_validation двох однакових елементів підряд
                                if ((node in node_in_validation["node_id"]) and (transaction == node_in_validation["transaction"])) == True: not_include = False
                            if not_include and node_is_valid:
                                self.nodes_in_validation.append({
                                    'node_id': node,
                                    'transaction': transaction,
                                    'status': valid_status,  #bool
                                    'timestamp': time()
                                })

                except: deactiveNode.add(node)

        if deactiveNode:                            #видаляються зі списку нод ноди які не відповіли на запит transaction/new
            print('transaction_validator')

            self.deactivate_node(deactiveNode, '')
        print('nodes_in_validation',self.nodes_in_validation)

        self.resolve_transaction_validation('', '')
        self.clear_trash_in_arrays()


        self_node = False  
        for node_in_validation in nodes_in_validation:        
            if ((self_node_adress in node_in_validation["node_id"]) and (transaction == node_in_validation["transaction"])) == True: 
                self_node = True
        if node_is_valid or self_node:
            for node_in_validation in nodes_in_validation:        
                if ((self_node_adress in node_in_validation["node_id"]) and (transaction == node_in_validation["transaction"])) == True: 
                    return node_in_validation["status"]
        else:   return "transaction already to mining"

    def resolve_transaction_validation(self, transaction, sender):
        # sleep(1)
        # print('1',self.nodes_in_validation)
        self_node_adress = f'{self.host}:{self.port}'
        nodes_in_validation = self.nodes_in_validation
        nodes = self.nodes
        transaction_resolver = self.transaction_resolver
        node_sum = []
        new_list = []
        inactive_nodes = set()


        for block in self.chain:
            include = False
            for chain_transaction in block['transactions']:
                if (chain_transaction == transaction): include = True
            if (transaction in self.current_transactions) or include:
                    return False


        for node_in_validation in self.nodes_in_validation:
            sum = 0
            rejected_node = 0
            number = 0
            not_include = True
            for node in nodes_in_validation:
                if node_in_validation['transaction'] == node['transaction']:
                    number = number + 1
                    if node['status'] == True:
                        sum = sum + 1
                    else: 
                        rejected_node = rejected_node + 1

            for value in node_sum:
                if value['transaction'] == node_in_validation['transaction']: not_include = False


            if not_include:
                node_sum.append({
                    'transaction': node_in_validation['transaction'],
                    'sum': sum,
                    'rejected': rejected_node,
                    'number': number,
                })





        print("node_sum: ",node_sum)
        print("nodes len",len(self.nodes))




        print('transaction:', transaction)
        if transaction:
            not_include = True            
            for resolved_transaction in self.transaction_resolver:
                if resolved_transaction['transaction'] == transaction:
                    not_include = False
                    if (sender in resolved_transaction['senders']) == False:
                        resolved_transaction['senders'].add(sender)
                        try:
                            requests.post(f'http://{sender}/transaction/resolve', json = {
                                'transaction': resolved_transaction['transaction'], 
                                'sender': self_node_adress
                                })
                        except: inactive_nodes.add(sender)

            if not_include:
                transaction_resolver.append({
                    'transaction': transaction,
                    'senders': {sender},
                    'timestamp': time()
                })
            if len(self.transaction_resolver) == 0:
                transaction_resolver.append({
                    'transaction': transaction,
                    'senders': {sender},
                    'timestamp': time()
                })        


        for value in node_sum:
            if value['sum']/len(self.nodes) >= 1:
                not_include = 0                                                             # 0 - True, 1 - False, 2 - inlcude transaction but not include selfnodeadress
                for resolved_transaction in self.transaction_resolver:
                    if resolved_transaction['transaction'] == value['transaction']: 
                        not_include = 1  
                        if (self_node_adress in resolved_transaction['senders']) == False:
                            not_include = 2 
                            resolved_transaction['senders'].add(self_node_adress)

                print(not_include)
                if not_include == 0 and ((value['transaction'] in self.current_transactions) == False):
                    self.transaction_resolver.append({
                        'transaction': value['transaction'],
                        'senders': set(),
                        'timestamp': time()
                    })
                    for transaction_resolve in self.transaction_resolver:
                        if transaction_resolve['transaction'] == value['transaction']:
                            transaction_resolve['senders'].add(self_node_adress)

                print(self.transaction_resolver)
                            
                if not_include != 1:
                    for node in nodes:
                        if node != self_node_adress:
                            try:
                                requests.post(f'http://{node}/transaction/resolve', json = {
                                    'transaction': value['transaction'], 
                                    'sender': self_node_adress
                                    })
                            except: inactive_nodes.add(node)

                if not_include == 2:
                    for transaction_resolve in transaction_resolver:
                        if transaction_resolve['transaction'] == value['transaction']:
                            transaction_resolve['senders'].add(self_node_adress)


        if inactive_nodes:
            print('resolve_transaction_validation')
            self.deactivate_node(inactive_nodes, '')
        print('transaction_resolver: ',self.transaction_resolver)
        

        for resolved_transaction in self.transaction_resolver:
            print(len(resolved_transaction['senders']))
            print(len(self.nodes))
            not_include = True
            if len(resolved_transaction['senders']) == len(self.nodes):
                for current_transaction in self.current_transactions:
                    if resolved_transaction['transaction'] == current_transaction:
                        not_include = False
                if (not_include):
                    self.current_transactions.append(resolved_transaction['transaction'])





        self.start_mining()
        self.clear_trash_in_arrays()


        print('transaction_resolver: ',self.transaction_resolver)
        print('nodes in validation:', self.nodes_in_validation)
        print('current_transactions:', self.current_transactions)
        
    def new_block(self, proof, previous_hash=None):
        transactions = []
        for current_transaction in self.current_transactions:
                not_include = True
                for value in self.chain:    
                    if (current_transaction in value['transactions']) == True:
                        not_include = False
                if not_include: transactions.append(current_transaction)

        transactions.append({
            'sender': 0,
            'recipient': node_identifier,
            'amount': 1,
        })

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Перезавантаження поточного списку транзакцій
        print("transactions in def new block \n", transactions, "\n")
        self.current_transactions = []


        self.chain.append(block)
        return block

    def clear_trash_in_arrays(self):
        new_list = []


        for node in self.nodes_in_validation:
            if (time()-node['timestamp']) < 30: #час за який ноди в списку валідованих нод рахуються недійсними
                new_list.append(node)
        self.nodes_in_validation = new_list
        new_list = []

        for transaction_resolver_element in self.transaction_resolver:
            if (time()-transaction_resolver_element['timestamp']) < 30:
                new_list.append(transaction_resolver_element)
        self.transaction_resolver = new_list
        new_list = []

        for mining_list_element in self.mining_list:
            if (time()-mining_list_element['timestamp']) < 60:
                new_list.append(mining_list_element)
        self.mining_list = new_list
        new_list = []

        for mining_resolver_element in self.mining_resolver:
            if (time()-mining_resolver_element['mining_data']['timestamp']) < 60:
                new_list.append(mining_resolver_element)
        self.mining_resolver = new_list
        new_list = []         

    def add_to_node_in_validation(self, values):

        if (values in self.nodes_in_validation) == False:
            self.nodes_in_validation.append(values)
   
    def node_register(self):
        self_node_adress = f'{self.host}:{self.port}'
        self.nodes.add(self_node_adress)
        for i in range(1010):
            try:

                response = requests.get(f'http://localhost:{"{:04d}".format(i+1)}/status')

                if response.status_code == 200:
                    node_list = response.json()['nodes']
                    print("Your node registet to "f'http://localhost:{"{:04d}".format(i+1)}')
                    for node in node_list:
                        if self.check_node_status(node):
                            self.nodes.add(node)
                    # print(self.nodes)
                    # self.resolve_conflicts()
                    
                    break
            except:
                if i == 9998 and (len(self.nodes) == 1):
                    print("Your node is first in network")

    def valid_nodes(self, node_Url, sender):
        # sleep(2)
        nodes = self.nodes
        added_nodes = self.added_nodes
        valid = True
        inactive_nodes = set()
        self_node_adress = f'{self.host}:{self.port}'



        if len(sender) > 0:
            added_nodes[0]['senders'].add(sender)

        for added in added_nodes[0]['added_nodes']:
            for node in node_Url:
                if added == node or node == self_node_adress: valid = False

        print("valid", valid)

        if valid:

            for node in node_Url:
                if node != self_node_adress:
                    if self.check_node_status(node):        
                        self.add_node(node)
                        added_nodes[0]['added_nodes'].append(node)  


            for node in nodes:
                if node != self_node_adress:
                    print("нода для відправки", node)
                    # added_nodes[0]['node_recipient'].append(node)
                    try:
                        requests.post(f'http://{node}/nodes/add', json = {"nodes": node_Url, "sender": self_node_adress})
                    except: 
                        inactive_nodes.add(node)
                        None

        if inactive_nodes:
            print('valid_nodes')
            self.deactivate_node(inactive_nodes)

        print('nodes:', self.nodes) 
        print('added nodes:',added_nodes[0])
        print(len(self.nodes)-1)
        print(len(added_nodes[0]['senders']))
        if (len(self.nodes)-1 == len(added_nodes[0]['senders'])):
            added_nodes[0]['added_nodes'] = []
            added_nodes[0]['senders'] = set()
            print('всі відправки пройшли')

    def check_node_status(self, node):
        self_node_adress = f'{self.host}:{self.port}'
        if self_node_adress != node:
            try:
                response = requests.get(f'http://{node}/status')
                if response.status_code == 200:
                    return True
            except: return False

    def deactivate_node(self, nodeUrl, sender):
 
        self_node_adress = f'{self.host}:{self.port}'
        nodes = self.nodes
        deleted_nodes = self.deleted_nodes
        nodes_in_validation = self.nodes_in_validation
        not_include = True

        if len(sender) > 0:
            self.deleted_nodes[0]['senders'].add(sender)

        for value in nodeUrl:
            if value in self.deleted_nodes[0]['deleted_nodes']: not_include = False

        if not_include:
            self.nodes = self.nodes - nodeUrl  #видаляєм ноди зі списку нод
            for node_in_validation in self.nodes_in_validation:   #якщо в nodes_in_validation є запис з нодою для видалення то міняємо статус валідації на False
                for node in nodeUrl:
                    if node == node_in_validation['node_id']:
                        node_in_validation['status'] = False

            for resolve_transaction in self.transaction_resolver:
                for node in nodeUrl:
                    if node in resolve_transaction['senders']:
                        resolve_transaction['senders'].remove(node) 

            print('nodes after delete',self.nodes)

            for value in nodeUrl:
                self.deleted_nodes[0]['deleted_nodes'].append(value)

            print('ноди для видалення',self.deleted_nodes)
            for node in nodes:
                if node != self_node_adress:
                    try:
                        print("нода для відправки", node)
                        requests.post(f'http://{node}/nodes/delete', json = {'nodes': list(nodeUrl), 'sender': self_node_adress})
                    except: None

        print('nodes:', self.nodes) 
        print('deleted nodes:',deleted_nodes[0])
        print(len(self.nodes)-1)
        print(len(deleted_nodes[0]['senders']))
        if (len(self.nodes)-1 == len(deleted_nodes[0]['senders'])):
            deleted_nodes[0]['deleted_nodes'] = []
            deleted_nodes[0]['senders'] = set()
            print('всі відправки пройшли')        

    def add_node(self, node):
        self.nodes.add(node)
        return f'{node} Has been added'

    def add_block(self, block):
        last_block = self.last_block
        previous_hash = blockchain.hash(last_block)
        if (previous_hash == block['previous_hash'] or len(self.chain) == 1) and ((block in self.chain) == False):
            self.chain.append(block)

            print('add blolck to chain:', block)
        self.current_transactions = []

    def valid_chain(self, chain):
        """
        Перевіряємо, чи є внесений до блоку хеш коректним
 
        """
 
        last_block = chain[0]
        current_index = 1
 
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Перевірте правильність хеша блоку
            if block['previous_hash'] != self.hash(last_block):
                return False
 
            # Перевіряємо, чи є підтвердження роботи коректним
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
 
            last_block = block
            current_index += 1
 
        return True
    
    def resolve_conflicts(self):
        """
        Це наш алгоритм Консенсусу, він вирішує конфлікти,
        замінюючи наш ланцюг на найдовший у мережі
 
        :return: <bool> True, якби наш ланцюг був замінений, False, якщо ні.
        """
 
        neighbours = self.nodes
        new_chain = None
 
        # Шукаємо тільки ланцюги, довші за наш
        max_length = len(self.chain)
 
        # Захоплюємо та перевіряємо всі ланцюги з усіх вузлів мережі
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
 
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
 
                # Перевіряємо, чи є довжина найдовшою, а ланцюг - валідним
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
 
        # Замінюємо наш ланцюг, якщо знайдемо інший валідний і довший
        if new_chain:
            self.chain = new_chain
            return True
 
        return False
    
    def proof_of_work(self, last_proof):

        self_node_adress = f'{self.host}:{self.port}'
        transactions = []
        for current_transaction in self.current_transactions:
            not_include = True
            for value in self.chain:    
                if (current_transaction in value['transactions']) == True:
                    not_include = False
            if not_include: transactions.append(current_transaction)
        print('transactioins: ', transactions)


        if len(transactions) == 2:
            proof = 0
            while self.valid_proof(last_proof, proof) is False:
                proof += 1
        

            # print("return mining validator: ", self.minig_validation(proof, time(), self_node_adress))
            # t = Thread(target=self.minig_validation, args=(proof, time(), self_node_adress))
            # t.start()
            # t.join()
            # print("sukaaaaaaaaaaaaaaaa")
            self.minig_validation(proof, time(), self_node_adress)
        # return a
    
    def start_mining(self):
        last_block = self.last_block
        last_proof = last_block['proof']
        self.proof_of_work(last_proof)

    def create_block(self, proof):
        self_node_adress = f'{self.host}:{self.port}'
        last_block = self.last_block
        inactive_nodes = set()
        transactions = []

        
        for current_transaction in self.current_transactions:
            not_include = True
            for value in self.chain:    
                if (current_transaction in value['transactions']) == True:
                    not_include = False
            if not_include: transactions.append(current_transaction)
        print('transactioins: ', transactions)


        if len(transactions) == 2:
            


            print("Створюємо новий блок шляхом внесення його в ланцюг")
            # Створюємо новий блок шляхом внесення його в ланцюг
            previous_hash = blockchain.hash(last_block)
            block = blockchain.new_block(proof, previous_hash)
            print(block)
            for node in self.nodes:
                if node != self_node_adress:
                    try:
                        print('11ytsduidsyiuys9fydsfuidsbfsyebcyuif')
                        requests.post(f'http://{node}/chain/addblock', json = {'block': block, 'sender': self_node_adress})
                    except: inactive_nodes.add(node)

        if inactive_nodes:
            print('start_mining')
            self.deactivate_node(inactive_nodes, '')

    def minig_validation(self, proof, timestamp, sender):
        self_node_adress = f'{self.host}:{self.port}'
        inactive_nodes = set()

          
        if proof > 0:
            not_include = True
            for resolved in self.mining_list:
                if resolved['proof'] == proof: not_include = False
            if not_include or sender == self_node_adress:
                    if not_include:
                        self.mining_list.append({
                            'proof': proof,
                            'senders': [{
                        'node_id': sender,
                        'timestamp': timestamp, 
                            }],
                            'timestamp': time()
                        })  
                    for node in self.nodes:
                        if node != sender and node != self_node_adress:
                            try:
                                requests.post(f'http://{node}/mining/validation', json = {
                                        'proof': proof,
                                        'timestamp': timestamp, 
                                        'sender': sender,
                                        'self_sender': self_node_adress
                                    })
                            except: inactive_nodes.add(node)
            

            for resolved in self.mining_list:
                not_include = True
                for id in resolved['senders']:
                    if sender == id['node_id']: not_include = False
                if not_include:
                    resolved['senders'].append({
                        'node_id': sender,
                        'timestamp': timestamp, 
                    })

            print('mining_list: ',self.mining_list)


            self.clear_trash_in_arrays()

            if inactive_nodes:
                print('minig_validation')
                self.deactivate_node(inactive_nodes, '')

            for mining_list_data in self.mining_list:
                if len(mining_list_data['senders']) == len(self.nodes):
                    self.mining_resolve('', '')

    def mining_resolve(self, data, sender):
        self_node_adress = f'{self.host}:{self.port}'
        resolve_timestamp = []
        inactive_nodes = set()



        for resolved in self.mining_list:
            first_timestamp = {
                'timestamp': 9999999999999.999999, #просто велике число якe має бути більшим за теоретичний timestamp
                'node_id': 'some id'
            }
            for tsm in resolved['senders']:
                if tsm['timestamp'] < first_timestamp['timestamp']:
                    first_timestamp['timestamp'] = tsm['timestamp']
                    first_timestamp['node_id'] = tsm['node_id']

            resolve_timestamp.append({
                'proof': resolved['proof'],
                'node_id': first_timestamp['node_id'],
                'timestamp': first_timestamp['timestamp']
            })
        
        print('resolve timestamp:', resolve_timestamp)
        print("self.mining_resolver: ", self.mining_resolver)


        if data:
            not_include = True
            for value in self.mining_resolver:
                if value['mining_data'] == data:
                    not_include = False
                    if (sender in value['senders']) == False:
                        value['senders'].add(sender)
                        try:
                            requests.post(f'http://{sender}/mining/resolver', json = {
                                'mining_data': value['mining_data'], 
                                'sender': self_node_adress
                                })
                        except: inactive_nodes.add(sender)
                        print('111111111`11111111111')
                        print(value['mining_data'])
            if not_include:
                self.mining_resolver.append({
                    'mining_data': data,
                    'senders': {sender}
                        })
            if len(self.mining_resolver) == 0:
                self.mining_resolver.append({
                    'mining_data': data,
                    'senders': {sender}
                })  




        for value in resolve_timestamp:
            not_include = 0                                                             # 0 - True, 1 - False, 2 - inlcude transaction but not include selfnodeadress
            for mining_data_data in self.mining_resolver:
                if mining_data_data['mining_data'] == value: 
                    not_include = 1  
                    if (self_node_adress in mining_data_data['senders']) == False:
                        not_include = 2 
                        mining_data_data['senders'].add(self_node_adress)


            if not_include == 0:
                self.mining_resolver.append({
                    'mining_data': value,
                    'senders': set()
                })
                for mining_data_data in self.mining_resolver:
                    if mining_data_data['mining_data'] == value:
                        mining_data_data['senders'].add(self_node_adress)


                        
            if not_include != 1:
                for node in self.nodes:
                    if node != self_node_adress:
                        try:
                            
                            requests.post(f'http://{node}/mining/resolver', json = {
                                'mining_data': value, 
                                'sender': self_node_adress
                                })
                        except: inactive_nodes.add(node)
                        print('22222222222222222')
                        print(value)
        print("nodes :\n", self.nodes ,"\n")
        print("nodes in validation: \n", self.nodes_in_validation, "\n")
        print("transaction resolver: \n", self.transaction_resolver, "\n")
        print("current transaction: \n", self.current_transactions, "\n")
        print("mining list: \n", self.mining_list, "\n")
        print("mining_resolver: \n", self.mining_resolver, "\n")
        # print("votes: \n", self.voteCalculator, "\n")


        self.clear_trash_in_arrays()


        if inactive_nodes:
            print('mining_resolve')
            self.deactivate_node(inactive_nodes, '')
        
        for mining_data in self.mining_resolver:
            if len(mining_data['senders'])/len(self.nodes) >= 1:
                print("len(mining_data['senders'])/len(self.nodes) >= 1 \n")
                if mining_data['mining_data']['node_id'] == self_node_adress and self.mining_resolver.index(mining_data) == len(self.mining_resolver)-1:
                    print("start adding block \n")
                    print("proof: ",mining_data['mining_data']['proof'])


                    self.create_block(mining_data['mining_data']['proof'])

    def voteCalculator(self):
        voteResult = []
        votes = []
        for block in self.chain:
            for transaction in block['transactions']:
                if transaction['sender'] != 0:
                    votes.append(transaction['recipient'])
        for vote in votes:
            not_include = True
            sum = 0

            for value in voteResult:
                if value['recipient'] == vote: not_include = False

            if not_include:
                for voteCheck in votes:
                    if vote == voteCheck:
                        sum = sum + 1
                voteResult.append({
                    "recipient": vote,
                    "numbers": sum
                })
        if voteResult:
            voteResult.sort(key=lambda x: x['numbers'], reverse=True)                
        return voteResult







    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):

        # Ми повинні переконатися, що словник упорядкований, інакше у нас будуть непослідовні хеші
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def valid_proof(self, last_proof, proof):


        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        if guess_hash[:4] == "0000": 
            print('proof:', proof)
            print('lastproof:', last_proof)
        return guess_hash[:4] == "0000"

@sio.event
def connect():
    print('connection established')

@sio.event
def call_data(data):
    print('message received with ', data)
    sio.emit('node_data', data)

@sio.event
def disconnect():
    print('disconnected from server')

sio.connect('http://localhost:5000')

# Створюємо екземпляр вузла
app = Flask(__name__)
CORS(app)

 
# Генеруємо унікальну на глобальному рівні адресу для цього вузла
node_identifier = str(uuid4()).replace('-', '')
 
# Створюємо екземпляр блокчейна
blockchain = Blockchain()

self_node_adress = f'{blockchain.host}:{blockchain.port}'


 
@app.route('/status', methods=['GET'])
def node_online_status():

    response = {
        "message": "I`m Online",
        "nodes": list(blockchain.nodes),
        "nodes_in_validation": list(blockchain.nodes_in_validation),
        # "transaction_resolver": list(blockchain.transaction_resolver),
        "current_transactions": list(blockchain.current_transactions),
        "mining_list": list(blockchain.mining_list),
        # "mining_resolver": blockchain.mining_resolver
        "vote_result": list(blockchain.voteCalculator())
    }

    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": "sender",
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    return jsonify(response), 200

@app.route('/nodes/add', methods=['POST'])
def add_nodes():
    values = request.get_json()
    node = values.get('nodes')
    sender = values.get('sender')
    print(f'node:{node}, sender:{sender}')

    if node is None:
        return "Error: Please supply a valid list of nodes", 400
    
 
    response = {
        'message': blockchain.valid_nodes(node, sender),
        'total_nodes': list(blockchain.nodes),
    }
    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": sender,
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    return jsonify(response), 200

@app.route('/chain/addblock', methods=['POST'])
def add_block_too_chain():
    values = request.get_json()
    block = values.get('block')
    sender = values.get('sender')


    print(f'wanna add block: {block}')

    if values is None:
        return "Error: Please supply a valid block", 400
    
    blockchain.add_block(block)
    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": sender,
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    return jsonify(list(blockchain.chain)), 200

@app.route('/nodes/delete', methods=['POST'])
def delete_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    sender = values.get('sender')
    node_set = set()
    
    for node in nodes:
        node_set.add(node)

    
    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": sender,
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    # response = list(blockchain.nodes)
    return jsonify(blockchain.deactivate_node(node_set, sender)), 202

@app.route('/mine', methods=['GET'])
def mine():
    # Ми запускаємо алгоритм підтвердження роботи, щоб отримати наступне підтвердження…
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
 
    # Ми повинні отримати винагороду за знайдене підтвердження
    # Відправник "0" означає, що вузол заробив крипто-монету
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )
 
    # Створюємо новий блок шляхом внесення його в ланцюг
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
 
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    transaction = values.get('transaction')
    sender = values.get('sender')
 
    # Переконайтеся, що необхідні поля знаходяться серед даних POST.
    required = ['sender', 'recipient', 'amount']
    if not all(k in transaction for k in required):
        return 'Missing values', 400
    

    print("транзакція залетіла", values)
    response = blockchain.transaction_validator(transaction['sender'], transaction['recipient'], transaction['amount'])

    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": sender,
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })

    return jsonify(response), 201

@app.route('/transactions/addtovalidation', methods=['POST'])
def transaction_to_validation():
    values = request.get_json()
    node_in_validation = values.get('node_in_validation')
    sender = values.get('sender')
    print("провалідована транзакція залетіла", node_in_validation)
    response = blockchain.add_to_node_in_validation(node_in_validation)
    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": sender,
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    return jsonify(response), 201

@app.route('/transaction/resolve', methods=['POST'])
def resolve_transactions():
    values = request.get_json()
    transaction = values.get('transaction')
    sender = values.get('sender')
    print('transaction reesolve',f'node:{transaction}, sender:{sender}')

    if transaction is None:
        return "Error: Please supply a valid list of nodes", 400
    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": sender,
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    response = {
        'message': blockchain.resolve_transaction_validation(transaction, sender),
        # 'transaction_resolver_list': list(blockchain.transaction_resolver),
    }
    return jsonify(response), 200

@app.route('/mining/validation', methods=['POST'])
def mining_validator():
    values = request.get_json()
    proof = values.get('proof')
    timestamp = values.get('timestamp')
    sender = values.get('sender')
    self_sender = values.get('self_sender')


    print('mining validation',f'proof:{proof}, timestamp:{timestamp}, sender:{sender}')

    if proof is None:
        return "Error: Please supply a valid list", 400
 
    response = {
        'message': blockchain.minig_validation(proof, timestamp, sender),
    }
    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": sender,
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    return jsonify(response), 200
 
@app.route('/mining/resolver', methods=['POST'])
def mining_resolve():
    values = request.get_json()
    data = values.get('mining_data')
    sender = values.get('sender')
    print('mining resolve',f'data:{data}, sender:{sender}')

    if data is None:
        return "Error: Please supply a valid list", 400
 
    response = {
        'message': blockchain.mining_resolve(data, sender),
    }
    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": sender,
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    return jsonify(response), 200
 
@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": "sender",
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    return jsonify(response), 200

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
 
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    call_data({
        "nodes": list(blockchain.nodes),
        "chain": list(blockchain.chain),
        "call_info": {
            "node_sender": "sender",
            "node_recipient": self_node_adress,
            },
        "voting_results": list(blockchain.voteCalculator())
        })
    return jsonify(response), 200



if __name__ == '__main__':
    app.run(blockchain.host, blockchain.port)

sio.wait()


















