# ----------------------------------------------------------------------------------------------------------
# Importações

from selenium.webdriver.common.by import By
from selenium import webdriver
from time import sleep as s
from netmiko import ConnectHandler
from tqdm import tqdm
import requests
import telnetlib
import re

# ----------------------------------------------------------------------------------------------------------
# Definições e Variaveis

options = webdriver.ChromeOptions()
options.add_argument("--headless")
n = webdriver.Chrome(options=options)

# circuito = input('digite o circuito : ')
ip_hw = '********'
porta_hw = '********'
usuario_hw = '********'
senha_hw = '*********'

ip_fiber = '********'
porta_fiber = '********'
usuario_fiber = '********'
senha_fiber = '********'

usuario_nokia = '********'
senha_nokia = '********'
porta_nokia = '********'

t = 0

with open('batimento_fibra.txt', 'r') as arquivo:
    circuitos = arquivo.readlines()

# ----------------------------------------------------------------------------------------------------------
# Executa Looping

for circuito in tqdm(circuitos):

    # ----------------------------------------------------------------------------------------------------------
    # Pega dados Connect Master

    link = f'https://********/CmCustomAPI/Consulta/{circuito}/NULL/NULL/'
    requisicao = requests.get(link)
    resposta = requisicao.json()
    dados_CM = []
    ipolt = resposta['ip_olt']
    tecnologia = resposta['tecnologia']
    serial = resposta['serial']
    dados_CM.append((ipolt, tecnologia, serial))

    # ----------------------------------------------------------------------------------------------------------
    # Executa se a tecnologia for HUAWEI

    if tecnologia == 'HUAWEI':

        try:
            telnet = telnetlib.Telnet(ip_hw, porta_hw, timeout=2)
        except Exception:
            print("Erro ao realizar a conexao!")
        telnet.write(f'LOGIN:::123::UN={usuario_hw},PWD={senha_hw};\n'.encode('utf-8'))
        s(1)
        telnet.write(f"LST-ONTDDMDETAIL::ALIAS={circuito}:9999::SHOWOPTION=OPTICSRXPOWERbyOLT;\n".encode('utf-8'))
        s(2)
        telnet.write(b'LOGOUT:::CTAG::;\n')

        data = telnet.read_until(b'Faz o L', timeout=2).decode('utf-8')
        # print(data)

        padrao = re.compile("-\d\d\d\d")
        busca = padrao.search(data)
        resultado = busca.group() if busca else str('alm')

        if resultado:
            primeiro_campo = resultado[0:3]
            segundo_campo = resultado[3:6]
            resultado = primeiro_campo + '.' + segundo_campo
            resultado2 = resultado
        if resultado == 'alm.':
            resultado = 'ONT sem sinal de fibra'
        elif resultado > '-25.00':
            resultado = 'Fibra Atenuada'
        else:
            resultado = 'Sinal de fibra OK!'
        try:
            with open('batimento_fibra_LOG.txt', 'a') as log:
                log.write(f'{circuito.rstrip()},{tecnologia}, {resultado2}, {resultado}\n')
        except Exception:
            pass
    # ----------------------------------------------------------------------------------------------------------
    # Executa se a tecnologia for FIBERHOME

    elif tecnologia == 'FIBERHOME':

        try:
            telnet = telnetlib.Telnet(ip_fiber, porta_fiber, timeout=5)
        except Exception:
            print("Erro ao realizar a conexao!")
        telnet.write(f'LOGIN:::001::UN={usuario_fiber},PWD={senha_fiber};\n'.encode('utf-8'))
        s(1)
        telnet.write(f"LST-ONU::OLTID={ipolt.rstrip()}:123::;\n".encode('utf-8'))
        s(3)
        telnet.write(b'LOGOUT:::000::;\n')

        data = telnet.read_until(b'Rage against the machine', timeout=10).decode('utf-8')
        # print(data)

        try:

            slot_porta = re.compile('\d-\d\d?-\d\d?-\d\d?\d?\s{1,100}\d\d?\d?\s{1,100}'f'{circuito.rstrip()}')
            busca_slot_porta = slot_porta.search(data)
            bloco_slot = busca_slot_porta.group() if busca_slot_porta else False
            # print(bloco_slot)

            redivisao = re.compile('\d\d?-\d\d?\s{1,100}')
            busca_redivisao = redivisao.search(bloco_slot)
            red = busca_redivisao.group() if busca_redivisao else False
            # print(red)

            padrao_slot = re.compile('\d\d?-')
            busca_slot = padrao_slot.search(red)
            slot = busca_slot.group() if busca_slot else False
            slot = slot.replace("-", "")
            # print(slot)

            padrao_porta = re.compile('-\d\d?\d?')
            busca_porta = padrao_porta.search(red)
            porta = busca_porta.group() if busca_porta else False
            porta = porta.replace("-", "")
            # print(porta)

            hg = re.compile(f'{circuito.rstrip()}''\s{1,100}\w{1,100}?-?\w{1,100}?-?\w{1,100}?\s{1,100}--'
                            '\s{1,100}MAC\s{1,100}\w{12}')
            busca_circuito1 = hg.search(data)
            lp1 = busca_circuito1.group() if busca_circuito1 else False
            # print(lp1)

            serial = re.compile('\w{12}')
            busca_serial = serial.search(lp1)
            nserial = busca_serial.group() if busca_serial else False
            # print(nserial)

            try:
                telnet = telnetlib.Telnet(ip_fiber, porta_fiber, timeout=5)
            except Exception:
                print("Erro ao realizar a conexao!")
            telnet.write(f'LOGIN:::001::UN={usuario_fiber},PWD={senha_fiber};\n'.encode('utf-8'))
            s(1)
            telnet.write(f'LST-OMDDM::OLTID={ipolt},PONID=NA-NA-{slot}-{porta},PEERFLAG=True,'
                         f'ONUIDTYPE=MAC,ONUID={nserial}:009::;\n'.encode('utf-8'))
            s(20)
            telnet.write(b'LOGOUT:::000::;\n')

            res = telnet.read_until(b'Rage Against The Machine', timeout=10).decode('utf-8')
            # print(res)

            padrao_sinal_fiber = re.compile('-\d\d[.]\d\d')
            busca_sinal_fiber = padrao_sinal_fiber.search(res)
            sinal_fiber = busca_sinal_fiber.group() if busca_sinal_fiber else str('alm')
            # print(sinal_fiber)

            if sinal_fiber == 'alm':
                resultado = 'ONT sem sinal de fibra'
            elif sinal_fiber > '-25.00':
                resultado = 'Fibra Atenuada'
            else:
                resultado = 'Sinal de fibra OK!'

            with open('batimento_fibra_LOG.txt', 'a') as log:
                log.write(f'{circuito.rstrip()}, {tecnologia}, {sinal_fiber}, {resultado}\n')
        except Exception:
            with open('batimento_fibra_LOG.txt', 'a') as log:
                log.write(f'{circuito.rstrip()}, {tecnologia}, ou não existe ou não tem circuito na gerencia \n')

    # ----------------------------------------------------------------------------------------------------------
    # Executa se a tecnologia for ZHONE

    elif tecnologia == 'ZHONE':
        try:
            telnet = telnetlib.Telnet(ipolt, '23', timeout=10)
            user = b'admin\n'
            password = b'zhone\n'

            telnet.read_until(b'login:')
            telnet.write(user)

            telnet.read_until(b'password:')
            telnet.write(password)
            s(1.5)
            telnet.write(f'onu find fsan {serial}\n'.encode('utf-8'))
            posicao = telnet.read_until(b'faz o L', timeout=15).decode('utf-8')
            # print(posicao)

            f_s_p = re.compile('\d/\d\d?/\d\d?\d?')
            busca_f_s_p = f_s_p.search(posicao)
            pos = busca_f_s_p.group() if busca_f_s_p else str('alm')
            # print(pos)

            s(3)
            telnet.write(f'onu power show {pos}\n'.encode('utf-8'))
            lista_sinal = telnet.read_until(b'faz o L', timeout=15).decode('utf-8')
            # print(lista_sinal)

            parametro_sinal01 = re.compile('-\d\d?[.]\d\d?\sdBm\s{1,500}-\d\d?[.]\d\d?\sdBm')
            busca_parametro_sinal01 = parametro_sinal01.search(lista_sinal)
            sinal01 = busca_parametro_sinal01.group() if busca_parametro_sinal01 else str('alm')
            # print(sinal01)

            parametro_sinal = re.compile('\s{1,100}-\d\d?[.]\d\d?\sdBm')
            busca_parametro_sinal = parametro_sinal.search(sinal01)
            sinal = busca_parametro_sinal.group() if busca_parametro_sinal else str('alm')
            sinal = sinal.replace("   ", "")
            # print(sinal)

            if sinal == 'alm':
                resultado_zms = 'ONT sem sinal de fibra'
            elif sinal > '-25.00 dBm':
                resultado_zms = 'Fibra Atenuada'
            else:
                resultado_zms = 'Sinal de fibra OK!'

            with open('batimento_fibra_LOG.txt', 'a') as log:
                log.write(f'{circuito.rstrip()}, {tecnologia}, {sinal.rstrip()}, {resultado_zms}\n')
        except Exception:
            with open('batimento_fibra_LOG.txt', 'a') as log:
                log.write(f'{circuito.rstrip()}, {tecnologia}, ou não existe ou não tem serial no CM\n')
    # ----------------------------------------------------------------------------------------------------------
    # Executa se a tecnologia for NOKIA

    elif tecnologia == 'NOKIA':
        try:
            device = {
                'device_type': 'alcatel_sros',
                'ip': f'{ipolt}',
                'port': 22,
                'username': 'isadmin',
                'password': 'ANS#150'
            }

            netconnect = ConnectHandler(**device)
            netconnect.send_command('environment inhibit-alarms mode interactive\n')
            output = netconnect.send_command_timing(f'info configure equipment ont interface flat | '
                                                    f'match exact:{circuito}', 70)

            print(output)

            parametro_posicao_nokia = re.compile('\d/\d/\d/\d\d?/\d\d?')
            busca_parametro_posicao_nokia = parametro_posicao_nokia.search(output)
            posicao_nokia = busca_parametro_posicao_nokia.group() if busca_parametro_posicao_nokia else False

            print(posicao_nokia)

            netconnect = ConnectHandler(**device)
            netconnect.send_command('environment inhibit-alarms mode interactive\n')
            output = netconnect.send_command_timing(f'show equipment ont optics {posicao_nokia}', 15)

            print(output)

            parametro_sinal_nokia = re.compile('-\d\d[.]\d\d?\d?')
            busca_parametro_sinal_nokia = parametro_sinal_nokia.search(output)
            sinal_nokia = busca_parametro_sinal_nokia.group() if busca_parametro_sinal_nokia else str('alm')

            if sinal_nokia == 'alm':
                resultado_nokia = 'ONT sem sinal de fibra'
            elif sinal_nokia > '-27.00':
                resultado_nokia = 'Fibra Atenuada'
            else:
                resultado_nokia = 'Sinal de fibra OK!'

            with open('batimento_fibra_LOG.txt', 'a') as log:
                log.write(f'{circuito.rstrip()}, {tecnologia}, {sinal_nokia}, {resultado_nokia}\n')
        except Exception:
            with open('batimento_fibra_LOG.txt', 'a') as log:
                log.write(f'{circuito.rstrip()}, {tecnologia}, ou não existe ou não tem serial no CM\n')

    # ----------------------------------------------------------------------------------------------------------
    # Executa se a tecnologia for CALIX

    elif tecnologia == 'CALIX':
        with open('batimento_fibra_LOG.txt', 'a') as log:
            log.write(f'{circuito.rstrip()}, {tecnologia}, tecnologia ainda não implementada no script \n')
    else:
        with open('batimento_fibra_LOG.txt', 'a') as log:
            log.write('Não foi possivel localizar os dados\n')