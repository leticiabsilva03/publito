# database/carga_dados.py
import pandas as pd
import asyncio
import logging
from datetime import date
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
import unidecode

# Importa os objetos de conexão e os modelos de tabela do seu projeto
from db_manager import database
from models import municipios, administracoes, municipios_administracoes, credenciais

# Configuração básica de logging para vermos o progresso no terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def seed_database():
    """
    Função principal que lê o CSV e popula o banco de dados.
    """
    # Garante que estamos conectados ao banco de dados para a operação
    await database.connect()
    
    try:
        # --- PASSO 1: LER E PREPARAR OS DADOS DO CSV ---
        logging.info("Lendo o ficheiro dados_sicom.csv...")
        # Lê o ficheiro CSV usando o ponto e vírgula como separador
        df = pd.read_csv('dados_sicom.csv', sep=';', dtype=str)
        # Substitui valores vazios (NaN) por None, que é o equivalente a NULL no banco
        df = df.where(pd.notna(df), None)
        logging.info(f"{len(df)} linhas lidas do CSV.")

        # --- PASSO 2: POPULAR AS TABELAS MESTRAS (MUNICIPIOS E ADMINISTRACOES) ---
        
        # 2.1 - Administrações
        logging.info("Populando a tabela 'administracoes'...")
        # Pega os valores únicos de sigla e descrição
        admins_unicas = df[['sigla_administracao', 'des_administracao']].drop_duplicates().to_dict('records')
        # Cria uma query de INSERT. O 'on_conflict_do_nothing' garante que, se uma sigla já existir,
        # a query não falhe, apenas ignora a inserção (ótimo para re-execuções).
        admin_insert_query = insert(administracoes).values(admins_unicas).on_conflict_do_nothing(
            index_elements=['sigla_administracao']
        )
        await database.execute(admin_insert_query)
        logging.info("Tabela 'administracoes' populada com sucesso.")

        # 2.2 - Municípios
        logging.info("Populando a tabela 'municipios'...")
        # Limpa e formata os nomes dos municípios antes de inserir
        df['nom_municipio_tratado'] = df['nom_municipio'].apply(lambda x: unidecode.unidecode(x).title() if pd.notna(x) else None)
        
        municipios_unicos = df[['nom_municipio_tratado', 'cnpj_municipio']].drop_duplicates()
        municipios_unicos = municipios_unicos.rename(columns={'nom_municipio_tratado': 'nom_municipio'}).to_dict('records')

        municipio_insert_query = insert(municipios).values(municipios_unicos).on_conflict_do_nothing(
            index_elements=['nom_municipio']
        )
        await database.execute(municipio_insert_query)
        logging.info("Tabela 'municipios' populada com sucesso.")
        
        # --- PASSO 3: BUSCAR OS IDs CRIADOS PARA MAPEAMENTO ---
        logging.info("Mapeando IDs das tabelas mestras...")
        # Busca todos os municípios e administrações que agora existem no banco
        db_municipios = await database.fetch_all(select(municipios.c.cod_municipio, municipios.c.nom_municipio))
        db_admins = await database.fetch_all(select(administracoes.c.cod_administracao, administracoes.c.sigla_administracao))
        
        # Cria dicionários de mapeamento para encontrar os IDs facilmente
        # Ex: {'Sao Paulo': 1, 'Recife': 2}
        municipio_map = {mun['nom_municipio']: mun['cod_municipio'] for mun in db_municipios}
        admin_map = {adm['sigla_administracao']: adm['cod_administracao'] for adm in db_admins}

        # --- PASSO 4: POPULAR A TABELA DE JUNÇÃO (MUNICIPIOS_ADMINISTRACOES) ---
        logging.info("Populando a tabela de junção 'municipios_administracoes'...")
        # Cria uma lista de dicionários com os pares de IDs de município e administração
        links_para_inserir = []
        for index, row in df.iterrows():
            cod_mun = municipio_map.get(row['nom_municipio_tratado'])
            cod_adm = admin_map.get(row['sigla_administracao'])
            if cod_mun and cod_adm:
                links_para_inserir.append({'cod_municipio': cod_mun, 'cod_administracao': cod_adm})
        
        # Remove duplicatas, caso existam no CSV
        links_unicos = [dict(t) for t in {tuple(d.items()) for d in links_para_inserir}]
        
        if links_unicos:
            link_insert_query = insert(municipios_administracoes).values(links_unicos).on_conflict_do_nothing(
                index_elements=['cod_municipio', 'cod_administracao']
            )
            await database.execute(link_insert_query)
        logging.info("Tabela de junção populada com sucesso.")
        
        # --- PASSO 5: BUSCAR OS IDs DA TABELA DE JUNÇÃO (COD_ENTIDADE) ---
        logging.info("Mapeando IDs da tabela de junção (entidades)...")
        db_entidades = await database.fetch_all(select(municipios_administracoes))
        # Mapeia pares (cod_municipio, cod_administracao) para o seu cod_entidade
        entidade_map = {(e['cod_municipio'], e['cod_administracao']): e['cod_entidade'] for e in db_entidades}

        # --- PASSO 6: FINALMENTE, POPULAR A TABELA DE CREDENCIAIS ---
        logging.info("Populando a tabela 'credenciais'...")
        credenciais_para_inserir = []
        for index, row in df.iterrows():
            cod_mun = municipio_map.get(row['nom_municipio_tratado'])
            cod_adm = admin_map.get(row['sigla_administracao'])
            
            # Pula linhas onde o cpf ou a senha são nulos
            if pd.isna(row['cpf_usuario']) or pd.isna(row['senha']):
                continue
                
            cod_ent = entidade_map.get((cod_mun, cod_adm))
            
            if cod_ent:
                credenciais_para_inserir.append({
                    'cod_entidade': cod_ent,
                    'cpf_usuario': row['cpf_usuario'],
                    'senha': row['senha'],
                    'data_atualizacao': date.today(),
                    'status_validade': True if row['status_validade'] == 'Validado' else False
                })

        if credenciais_para_inserir:
            # Não usamos 'on_conflict' aqui porque cada linha do CSV deve ser uma credencial única
            await database.execute_many(query=insert(credenciais), values=credenciais_para_inserir)
        
        logging.info(f"Tabela 'credenciais' populada com sucesso! {len(credenciais_para_inserir)} credenciais inseridas.")

    finally:
        # Garante que a conexão com o banco seja fechada ao final da operação
        await database.disconnect()
        logging.info("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    # Executa a função assíncrona principal
    asyncio.run(seed_database())
