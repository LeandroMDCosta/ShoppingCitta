import logging
import os
from typing import List, Dict
from selenium import webdriver 
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from time import sleep

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class shoppingCitta:
    def __init__(self, headless: bool = True):
        self.url = "https://cittaofficemall.com.br/site/lojas/"
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 20)

    def _setup_driver(self, headless: bool) -> webdriver.Firefox:
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        
        # User-agent para evitar bloqueios
        options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0")
        
        driver = webdriver.Firefox(options=options)
        driver.set_window_size(1920, 1080)
        return driver

    def pegar_todas_lojas(self) -> List[dict]:
        lista_de_lojas = []
        lojas = self.driver.find_elements(By.CLASS_NAME, "kw-listing-item")

        for loja in lojas:
            try:

                nome = loja.find_element(By.CLASS_NAME, "kw-listing-item-title").text.strip()
                localizacao = loja.find_element(By.CLASS_NAME, "kw-listing-item-location").text.strip()
                
               
                lista_de_lojas.append({
                    "nome": nome,
                    "localizacao": localizacao
                    })
            except Exception as e:
                continue
        return lista_de_lojas
    
    def run(self) -> List[dict]:
        todas_lojas = []
        try:
            logging.info(f"Acessando {self.url}...")
            self.driver.get(self.url)

           
            while True:
                try:
                   
                    botao = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "load_more_jobs")))
                    
                    self.driver.execute_script("arguments[0].scrollIntoView();", botao)
                    sleep(1)
                    self.driver.execute_script("arguments[0].click();", botao)
                    
                    logging.info("Carregando mais lojas...")
                    sleep(2)
                except (TimeoutException, NoSuchElementException):
                    logging.info("Todas as lojas carregadas na tela.")
                    break
                except Exception as e:
                    logging.warning(f"Interrupção no carregamento: {e}")
                    break

            
            logging.info("Iniciando extração dos dados...")
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "kw-listing-item")))
            todas_lojas = self.pegar_todas_lojas()
          
        except Exception as e:
            logging.error(f"Erro inesperado: {e}")
        finally:
            self.driver.quit()
            logging.info(f"Processo finalizado. Total capturado: {len(todas_lojas)}")
        return todas_lojas

    def save_to_csv(self, dados: List[Dict], filename: str = "lojas_citta.csv"):
        if not dados:
            logging.warning("Sem dados para salvar.")
            return
        
        
        diretorio = os.path.dirname(os.path.abspath(__file__))
        caminho_completo = os.path.join(diretorio, filename)
        
        df = pd.DataFrame(dados)
        df = df.drop_duplicates(subset=['nome'])
        df.to_csv(caminho_completo, index=False, encoding='utf-8-sig')
        logging.info(f"Arquivo salvo com sucesso em: {caminho_completo}")

if __name__ == "__main__":
    scraper = shoppingCitta(headless=True)
    resultado = scraper.run()

    if resultado:
        print(f"\n--- SUCESSO ---")
        print(f"Total de lojas únicas: {len(resultado)}")
        scraper.save_to_csv(resultado)
    else:
        print("\nErro: Nenhum dado foi coletado.")