import requests
from bs4 import BeautifulSoup
import pandas as pd
from pandasgui import show
from lxml import etree
import re

def clean_text(text):
    if text is None:
        return ''
    
    # Rimuove i caratteri di tabulazione e sostituisce con uno spazio
    text = text.replace('\t', ' ')
    
    # Rimuove gli a capo e le nuove righe
    text = re.sub(r'\n+', ' ', text)  # Sostituisce le nuove righe con uno spazio
    
    # Rimuove spazi bianchi multipli e riduce a uno solo
    text = re.sub(r'\s+', ' ', text)
    
    # Rimuove spazi bianchi all'inizio e alla fine
    text = text.strip()
    
    return text

def fetch_table_data(base_url):
    response = requests.get(base_url)
    if response.status_code != 200:
        print(f"Errore {response.status_code} durante il download della pagina.")
        return [], [], []

    # Parsing con lxml
    tree = etree.HTML(response.content)

    table_rows = tree.xpath('/html/body/div/div[4]/div[3]/table')
    
    # Estrai intestazioni
    header_rows = table_rows[0].xpath('./tr[1]')

    headers = []
    if header_rows:
        header_columns = header_rows[0].xpath('th')
        headers = [col.text.strip() if col.text else '' for col in header_columns]
    else:
        print("Nessuna intestazione trovata.")

    links = []

    # Estrai dati della tabella
    table_data_rows = table_rows[0].xpath('./tbody/tr')
    table_data  = []
    for row in table_data_rows:
        row_data = []
        columns = row.xpath('td')
        
        for i, col in enumerate(columns):
            temp = []
            spans = col.xpath('span')
            # concatena tutti gli spans
            if spans:
                for span in spans:
                    a = span.xpath('a')
                    if a:
                        for link in a:
                            links.append(link.attrib['href'])
                            link_text = link.text.strip() if link.text else ''
                            temp.append(link_text)

                    temp.append(span.text.strip() if span.text else '')
                if i == 5:
                    row_data.append(', '.join(temp))
                else:
                    row_data.append(' '.join(temp))
            else:
                row_data.append(col.text.strip() if col.text else '')
        table_data.append(row_data)
    
    return headers, table_data, links

def fetch_content_from_links(links):
    contents = []
    for link in links:
        try:
            response = requests.get(link, verify=False)
            response.raise_for_status()  # Solleva un'eccezione per codici di stato HTTP errati
        except requests.RequestException as e:
            print(f"Errore durante il download della pagina {link}: {e}")
            contents.append('')
            continue
        # Parsing con lxml
        tree = etree.HTML(response.content)
        div_with_h3 = tree.xpath('//div[h3="MODALITA\' D\'ESAME"]')
        if not div_with_h3:
            div_with_h3 = tree.xpath('//div[h3="EXAM DESCRIPTION"]')
            if not div_with_h3:
                print(f"Non trovato il div con MODALITA' D'ESAME per il link {link}")
                contents.append('')
                continue

        # Estrai tutto il testo all'interno del div
        content_div = div_with_h3[0]
        content = ''.join(content_div.xpath('.//text()')).strip()  # Estrae il testo completo, escludendo il markup HTML
        
        content = content.replace("MODALITA' D'ESAME", "").strip()
        content = content.replace("EXAM DESCRIPTION", "").strip()
        contents.append(content)

    return contents

def filter_rows_by_blacklist(rows, blacklist):
    filtered_rows = []
    for row in rows:
        row = [clean_text(cell) for cell in row]
        # Verifica se qualche parola nella riga è nella blacklist o è vuota
        if any(word.lower() in ' '.join(row).lower() for word in blacklist) or not any(row):
            continue  # Salta questa riga se contiene parole della blacklist
        filtered_rows.append(row)
        
    return filtered_rows

def main():
    base_url = 'https://servizionline.unige.it/unige/stampa_manifesto/MF/2024/8759.html'
    headers, table_data, links = fetch_table_data(base_url)
    headers.append('Modalità d\'esame')
    
    # Lista nera delle parole
    blacklist = [
        'insegnamenti', 'ateneo'
    ]

    # Filtra righe basandosi sulla blacklist
    filtered_data = filter_rows_by_blacklist(table_data, blacklist)
    
    # Ottieni contenuti dai link
    link_contents = fetch_content_from_links(links)

    for i, row in enumerate(filtered_data):
        if i < len(link_contents):
            row.append(clean_text(link_contents[i]))
        else:
            row.append('')
    
    # Crea un DataFrame e salva in CSV
    if filtered_data:
        
        # Crea il DataFrame
        try:
            df = pd.DataFrame(filtered_data, columns=headers)
            df.to_csv('output.csv', index=False)
            print("Dati salvati in output.csv")
            show(df)
        except Exception as e:
            print(f"Errore durante la creazione del DataFrame: {e}")
    else:
        print("Nessun dato trovato per creare il DataFrame.")

if __name__ == "__main__":
    main()
