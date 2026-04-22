import logging
import os
import pandas as pd
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Configuração global de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CittaMallScraper:
    
    def __init__(self, headless: bool = True):
        self.url = "https://cittaofficemall.com.br/site/lojas/"
        self.headless = headless
        self.driver = None
        self.wait = None

    def __enter__(self):
        self._setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
            logging.info("Browser finalizado.")

    def _setup_driver(self):
        options = webdriver.FirefoxOptions()
        if self.headless:
            options.add_argument("--headless")
        
        options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0")
        
        self.driver = webdriver.Firefox(options=options)
        self.driver.set_window_size(1920, 1080)
        self.wait = WebDriverWait(self.driver, 15)

    def _extract_stores_from_page(self) -> List[Dict[str, str]]:
        extracted_data = []
        stores = self.driver.find_elements(By.CLASS_NAME, "kw-listing-item")

        for store in stores:
            try:
                nome = store.find_element(By.CLASS_NAME, "kw-listing-item-title").text.strip()
                localizacao = store.find_element(By.CLASS_NAME, "kw-listing-item-location").text.strip()
                extracted_data.append({"nome": nome, "localizacao": localizacao})
            except StaleElementReferenceException:
                continue
            except Exception as e:
                logging.warning(f"Falha ao extrair dados de uma loja específica. Erro: {e}")
                continue
                
        return extracted_data

    def run(self) -> List[Dict[str, str]]:
        logging.info(f"Acessando {self.url}...")
        self.driver.get(self.url)

        while True:
            try:
                # Espera o botão existir e ser clicável
                button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "load_more_jobs")))
                
                # Conta quantas lojas existem ANTES de clicar
                current_store_count = len(self.driver.find_elements(By.CLASS_NAME, "kw-listing-item"))
                
                self.driver.execute_script("arguments[0].scrollIntoView();", button)
                self.driver.execute_script("arguments[0].click();", button)
                logging.info("Botão 'Carregar mais' clicado...")
                
                # Aguarda até que o número de lojas seja maior que o anterior
                self.wait.until(
                    lambda driver: len(driver.find_elements(By.CLASS_NAME, "kw-listing-item")) > current_store_count
                )
                
            except (TimeoutException, NoSuchElementException):
                logging.info("Todas as lojas foram carregadas ou botão sumiu.")
                break
            except Exception as e:
                logging.warning(f"Interrupção inesperada no carregamento: {e}")
                break

        logging.info("Iniciando extração final dos dados...")
        return self._extract_stores_from_page()


def save_to_csv(dados: List[Dict], filename: str = "lojas_citta.csv"):
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
    with CittaMallScraper(headless=True) as scraper:
        resultado = scraper.run()

    if resultado:
        print(f"\n--- SUCESSO ---")
        print(f"Total de lojas extraídas (antes da deduplicação): {len(resultado)}")
        save_to_csv(resultado)
    else:
        print("\nErro: Nenhum dado foi coletado.")