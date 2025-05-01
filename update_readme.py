# ---
import requests
import os
import logging
import base64
import urllib.parse
from datetime import datetime, timedelta

# --- configurações e constantes --- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("update_readme.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

USERNAME = "esscova"
MONOREPO_NAMES = ["ML-DL", "estudos", "testdrive"]  
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MAX_UPDATES = 5  
EXCLUDED_REPOS = ["esscova"]  

README_STATIC_CONTENT = """<h1><img src="https://emojis.slackmojis.com/emojis/images/1643514418/3958/storm_trooper.gif?1643514418" width="30"/> Hey! Nice to see you.</h1>
<p>Hi, I'm Wellington, Data Scientist & Engineer</p>

<h3>Things I code with</h3>
<p>
  <img alt="Python" src="https://img.shields.io/badge/-Python-000?style=flat-square&logo=python&logoColor=white" />
  <img alt="R" src="https://img.shields.io/badge/-R-000000?style=flat-square&logo=r&logoColor=white" />
  <img alt="Nodejs" src="https://img.shields.io/badge/-Nodejs-000?style=flat-square&logo=Node.js&logoColor=white" />
  <img alt="React" src="https://img.shields.io/badge/-React-000000?style=flat-square&logo=react&logoColor=white" />
  <img alt="Docker" src="https://img.shields.io/badge/-Docker-000?style=flat-square&logo=docker&logoColor=white" />
  <img alt="SQLite" src="https://img.shields.io/badge/-SQLite-000000?style=flat-square&logo=sqlite&logoColor=white" />
  <img alt="MySQL" src="https://img.shields.io/badge/-MySQL-000?style=flat-square&logo=mysql&logoColor=white" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/-PostgreSQL-000000?style=flat-square&logo=postgresql&logoColor=white" />
  <img alt="Linux" src="https://img.shields.io/badge/-Linux-000000?style=flat-square&logo=linux&logoColor=white" />
  <img alt="Visual Studio Code" src="https://img.shields.io/badge/-VSCode-000000?style=flat-square&logo=visual-studio-code&logoColor=white" />
</p>

<h3>Where to find me</h3>
<p>
  <a href="https://github.com/esscova" target="_blank"><img alt="Github" src="https://img.shields.io/badge/GitHub-%2312100E.svg?&style=for-the-badge&logo=Github&logoColor=white" /></a>
  <a href="https://www.linkedin.com/in/wellington-moreira-santos" target="_blank"><img alt="LinkedIn" src="https://img.shields.io/badge/linkedin-%230077B5.svg?&style=for-the-badge&logo=linkedin&logoColor=white" /></a>
  <a href="mailto:wmoreira.ds@gmail.com"><img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white"/> </a>
</p>

<h3>Last updates</h3>
"""
# --- funções --- #
def get_all_repos():
    logger.info("Coletando repositórios do usuário %s", USERNAME)
    repos = []
    page = 1
    per_page = 100
    while True:
        url = f"https://api.github.com/users/{USERNAME}/repos?per_page={per_page}&page={page}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error("Erro na API (repos): %s", response.status_code)
            break
        page_repos = response.json()
        if not page_repos:
            logger.info("Nenhuma página adicional de repositórios encontrada")
            break
        repos.extend(page_repos)
        logger.info("Coletados %d repositórios na página %d", len(page_repos), page)
        page += 1
    logger.info("Total de repositórios coletados: %d", len(repos))
    return repos

def get_latest_commit(repo_name, path=None):
    logger.info("Buscando último commit para %s%s", repo_name, f"/{path}" if path else "")
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/commits"
    params = {"per_page": 1}
    if path:
        params["path"] = path
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200 or not response.json():
        logger.warning("Nenhum commit encontrado ou erro na API para %s: %s", repo_name, response.status_code)
        return None
    commit = response.json()[0]
    logger.info("Commit encontrado para %s: %s", repo_name, commit["sha"])
    return {
        "sha": commit["sha"],
        "message": commit["commit"]["message"],
        "date": commit["commit"]["author"]["date"],
        "url": commit["html_url"]
    }

def get_monorepo_projects(repo_name):
    logger.info("Coletando projetos do monorepo %s", repo_name)
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/contents"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.error("Erro ao coletar conteúdos do monorepo %s: %s", repo_name, response.status_code)
        return []
    contents = response.json()
    projects = [item["path"] for item in contents if item["type"] == "dir"]
    logger.info("Projetos encontrados no monorepo %s: %s", repo_name, projects)
    return projects

def get_project_description(repo_name, project_path):
    logger.info("Buscando descrição para %s/%s", repo_name, project_path)
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/contents/{project_path}/README.md"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.warning("Nenhum README.md encontrado para %s/%s", repo_name, project_path)
        return f"Projeto no monorepo {repo_name}"
    content = response.json()
    if "content" not in content:
        logger.warning("README.md vazio para %s/%s", repo_name, project_path)
        return f"Projeto no monorepo {repo_name}"
    
    decoded_content = base64.b64decode(content["content"]).decode("utf-8")
    # Extrai a primeira linha não vazia, preferindo títulos (#)
    lines = [line.strip() for line in decoded_content.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("#"):
            description = line.lstrip("#").strip()
            logger.info("Descrição (título) encontrada para %s/%s: %s", repo_name, project_path, description)
            return description
        if not line.startswith(("#", "<", "!")):  # Evita tags HTML/Markdown
            logger.info("Descrição (primeira linha) encontrada para %s/%s: %s", repo_name, project_path, line)
            return line
    logger.warning("Nenhuma descrição válida encontrada para %s/%s", repo_name, project_path)
    return f"Projeto no monorepo {repo_name}"

def update_readme():
    logger.info("Iniciando atualização do README")
    repos = get_all_repos()
    updates = []

    # atualizações de repositórios normais, excluindo repositórios especificados
    for repo in repos:
        if repo["name"] in MONOREPO_NAMES:
            logger.info("Ignorando monorepo %s", repo["name"])
            continue
        if repo["name"] in EXCLUDED_REPOS:
            logger.info("Ignorando repositório excluído %s", repo["name"])
            continue
        commit = get_latest_commit(repo["name"])
        if commit:
            updates.append({
                "name": repo["name"],
                "type": "repo",
                "description": repo["description"] or "Sem descrição",
                "commit_message": commit["message"],
                "commit_date": commit["date"],
                "commit_url": commit["url"],
                "repo_url": repo["html_url"]
            })

    # atualizações de todos os monorepos
    for monorepo in MONOREPO_NAMES:
        monorepo_projects = get_monorepo_projects(monorepo)
        for project in monorepo_projects:
            commit = get_latest_commit(monorepo, path=project)
            if commit:
                description = get_project_description(monorepo, project)
                # Codifica a URL para lidar com espaços e caracteres especiais
                encoded_project = urllib.parse.quote(project)
                # Usa apenas o nome do diretório no texto do link
                link_text = f"{monorepo}/{project.split(' - ')[0]}".strip()
                updates.append({
                    "name": link_text,
                    "type": "project",
                    "description": description,
                    "commit_message": commit["message"],
                    "commit_date": commit["date"],
                    "commit_url": commit["url"],
                    "repo_url": f"https://github.com/{USERNAME}/{monorepo}/tree/main/{encoded_project}"
                })

    # Ordena por data de commit (mais recente primeiro)
    updates.sort(key=lambda x: x["commit_date"], reverse=True)
    updates = updates[:MAX_UPDATES]  # Limita ao número máximo de atualizações
    logger.info("Total de atualizações coletadas: %d", len(updates))

    # Gera a seção de atualizações
    updates_content = ""
    for update in updates:
        date = datetime.strptime(update["commit_date"], "%Y-%m-%dT%H:%M:%SZ")
        formatted_date = date.strftime("%d/%m/%Y")
        updates_content += (
            f"<p>\n"
            f"<a href=\"{update['repo_url']}\" target=\"_blank\">{update['name']}</a> ({formatted_date}): "
            f"{update['description']}\n"
            f"</p>\n\n"
        )

    # concatenar o conteúdo fixo com a seção de atualizações
    readme_content = f"{README_STATIC_CONTENT}{updates_content}---\n"
    logger.info("Conteúdo do README gerado com sucesso")

    # Salva o README
    with open("README.md", "w") as file:
        file.write(readme_content)
    logger.info("README salvo em README.md")

if __name__ == "__main__":
    update_readme()
