import scrapy
import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

class CittamallSpider(scrapy.Spider):
    name = 'cittamall'

    def __init__(self, headless: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headless = headless
        
        # Estrutura de armazenamento
        self.df = {
            'shopping_administrator': [],
            'shopping_name': [],
            'shopping_site': [],
            'shopping_data_url': [],
            'store_name': [],
            'store_floor': [],
            'store_site': [],
            'store_phone': [],
            'store_type': [],
            'source_page': []
        }
        
        # Configurações do Chrome
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        
        # Inicializando o Chrome
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_window_size(1920, 1080)
        self.wait = WebDriverWait(self.driver, 15)

    def start_requests(self):
        shopping_administrator = 'Citta Office Mall'
        shopping_list = [
            {
                'shopping_name': 'Citta Office Mall',
                'shopping_site': 'https://cittaofficemall.com.br/site',
                'shopping_data_url': 'https://cittaofficemall.com.br/site/lojas/'
            }
        ]
        
        for shopping in shopping_list:
            yield scrapy.Request(
                url=shopping['shopping_data_url'],
                meta={
                    'shopping_name': shopping['shopping_name'], 
                    'admin': shopping_administrator,
                    'shopping_site': shopping['shopping_site']
                },
                dont_filter=True
            )
         
    def parse(self, response):
        logging.info("Processando: Citta Office Mall")
        
        try:
            self.driver.get(response.url)
            
            # Loop para clicar no botão "Carregar mais"
            while True:
                try:
                    button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "load_more_jobs")))
                    current_store_count = len(self.driver.find_elements(By.CLASS_NAME, "kw-listing-item"))
                    
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    
                    posicao_anterior = None
                    while True:
                        posicao_atual = button.location['y']
                        if posicao_atual == posicao_anterior:
                            break 
                        posicao_anterior = posicao_atual
                        time.sleep(0.2)
                        
                    self.driver.execute_script("arguments[0].click();", button)
                    logging.info("Botão 'Carregar mais' clicado...")
                    
                    # Aguarda até que o número de lojas listadas aumente
                    self.wait.until(
                        lambda driver: len(driver.find_elements(By.CLASS_NAME, "kw-listing-item")) > current_store_count
                    )
                    
                except (TimeoutException, NoSuchElementException):
                    logging.info("Todas as lojas foram carregadas ou o botão desapareceu.")
                    break
                except Exception as e:
                    logging.warning(f"Interrupção inesperada no carregamento: {e}")
                    break

            # Extração dos dados
            stores = self.driver.find_elements(By.CLASS_NAME, "kw-listing-item")
            logging.info(f"Iniciando extração. Total de elementos encontrados: {len(stores)}")

            for store in stores:
                try:
                    nome_da_loja = store.find_element(By.CLASS_NAME, "kw-listing-item-title").text.strip()
                    localizacao = store.find_element(By.CLASS_NAME, "kw-listing-item-location").text.strip()
                    
                    # 1. Alimentando o self.df (caso você use em algum pipeline customizado no closed)
                    self.df['shopping_administrator'].append(response.meta['admin'])
                    self.df['shopping_name'].append(response.meta['shopping_name'])
                    self.df['shopping_site'].append(response.meta['shopping_site'])
                    self.df['shopping_data_url'].append(response.url)
                    self.df['store_name'].append(nome_da_loja)
                    self.df['store_floor'].append(localizacao)
                    self.df['store_site'].append(None)
                    self.df['store_phone'].append(None)
                    self.df['store_type'].append(None)
                    self.df['source_page'].append('lojas')
                    
                   
                    
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    logging.warning(f"Falha ao extrair dados de uma loja específica. Erro: {e}")
                    
        except Exception as e:
            logging.error(f"Erro geral ao processar a página: {e}")

    def closed(self, reason):
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
            logging.info("Navegador Chrome fechado com sucesso.")

        total_lojas = len(self.df['store_name'])
        logging.info(f"Rendimento total: {total_lojas} lojas raspadas. Iniciando envio para o Pipeline...")