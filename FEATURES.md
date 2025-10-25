# MCP Obsidian - Recursos Inteligentes

## Funcionalidades Implementadas

### Fase 1: Discovery & Introspection ✅

O servidor MCP agora possui inteligência contextual para entender automaticamente a estrutura do seu vault.

#### Novos Tools Disponíveis

1. **`obsidian_analyze_vault_structure`**
   - Analisa toda a estrutura do vault
   - Detecta automaticamente:
     - Padrão de organização de Daily Notes (ex: `Daily Notes/YYYY/MM - Month/YYYY-MM-DD.md`)
     - Pasta de Pessoas (ex: `People/`)
     - Estrutura de Projetos (ex: `Projetos/Empresa/Projeto/`)
     - Schemas comuns de frontmatter
   - Salva configuração detectada em `vault-config.json`

   **Exemplo de uso:**
   ```json
   {
     "tool": "obsidian_analyze_vault_structure",
     "args": {
       "save_config": true
     }
   }
   ```

2. **`obsidian_analyze_frontmatter`**
   - Analisa padrões de frontmatter em uma pasta específica
   - Detecta:
     - Campos comuns e suas frequências
     - Tipos de dados esperados
     - Campos faltantes em algumas notas
   - Sugere melhorias para consistência

   **Exemplo de uso:**
   ```json
   {
     "tool": "obsidian_analyze_frontmatter",
     "args": {
       "folder_path": "People",
       "sample_size": 20
     }
   }
   ```

3. **`obsidian_suggest_frontmatter`**
   - Analisa uma nota específica
   - Compara com notas similares na mesma pasta
   - Sugere campos de frontmatter para adicionar
   - Detecta inconsistências de tipo

   **Exemplo de uso:**
   ```json
   {
     "tool": "obsidian_suggest_frontmatter",
     "args": {
       "note_path": "People/Igor Curi.md",
       "reference_folder": "People"
     }
   }
   ```

4. **`obsidian_get_folder_context`**
   - Retorna contexto rico sobre uma pasta
   - Identifica o propósito da pasta (Daily Notes, People, Projects, etc)
   - Estatísticas (número de arquivos, subpastas)
   - Padrões de frontmatter
   - Útil para o agente entender o contexto antes de trabalhar em uma pasta

   **Exemplo de uso:**
   ```json
   {
     "tool": "obsidian_get_folder_context",
     "args": {
       "folder_path": "Projetos/BeSolution"
     }
   }
   ```

### Sistema de Configuração

O servidor agora mantém um arquivo `vault-config.json` com:
- Estrutura detectada do vault
- Schemas de frontmatter
- Padrões organizacionais
- Preferências de features

**Exemplo de `vault-config.json`:**
```json
{
  "daily_notes": {
    "detected_pattern": "Daily Notes/YYYY/MM - Month Name/YYYY-MM-DD.md",
    "detected_sections": [
      "Resumo do Dia",
      "Projetos do Dia",
      "Registro de Ações (Tasks)",
      "Reuniões",
      "Decisões e Bloqueios",
      "Notas Rápidas"
    ],
    "frontmatter_fields": ["type", "tags", "date", "time", "mentions"]
  },
  "people": {
    "detected_folder": "People",
    "detected_schema": {}
  },
  "projects": {
    "detected_folders": ["Projetos"],
    "hierarchy_pattern": "Company/Project",
    "detected_schema": {}
  }
}
```

### Melhorias no Cliente Obsidian API

- `list_files_in_vault()` agora retorna objeto completo com metadados
- `list_files_in_directory(path)` como alias consistente
- `get_file_contents(path, return_json=True)` para obter nota com metadata completa

## Como Usar

### 1. Primeiro Uso - Análise Inicial

```bash
# O agente deve executar este comando primeiro para entender seu vault:
obsidian_analyze_vault_structure
```

Isso criará o arquivo `vault-config.json` com toda a estrutura detectada.

### 2. Analisar Padrões de Frontmatter

```bash
# Analisar pasta de pessoas
obsidian_analyze_frontmatter --folder_path "People"

# Analisar pasta de projetos de uma empresa
obsidian_analyze_frontmatter --folder_path "Projetos/BeSolution"
```

### 3. Melhorar Nota Específica

```bash
# Sugerir melhorias para nota de pessoa
obsidian_suggest_frontmatter --note_path "People/Igor Curi.md"
```

### 4. Entender Contexto de Pasta

```bash
# Antes de trabalhar em uma pasta, entender seu propósito
obsidian_get_folder_context --folder_path "Projetos"
```

## Workflows Inteligentes

### Workflow 1: Padronizar Frontmatter em Pasta Pessoas

1. Analisar padrões existentes:
   ```
   obsidian_analyze_frontmatter --folder_path "People"
   ```

2. Para cada pessoa com frontmatter incompleto:
   ```
   obsidian_suggest_frontmatter --note_path "People/[Nome].md"
   ```

3. Aplicar sugestões usando `obsidian_patch_content`

### Workflow 2: Criar Nova Nota com Contexto

1. Entender contexto da pasta:
   ```
   obsidian_get_folder_context --folder_path "People"
   ```

2. Criar nota com frontmatter apropriado baseado no schema detectado

### Workflow 3: Organizar Projetos

1. Analisar estrutura de projetos:
   ```
   obsidian_analyze_vault_structure
   ```

2. Verificar contexto de subpasta:
   ```
   obsidian_get_folder_context --folder_path "Projetos/BeSolution"
   ```

3. Criar novos projetos seguindo o padrão detectado

## Próximas Funcionalidades (Roadmap)

### Fase 2: Navegação Semântica (Próxima)
- Busca por similaridade semântica
- Análise de relacionamentos entre notas
- Sugestão de links automáticos

### Fase 3: Sistema de Templates
- Detecção automática de templates
- Aplicação inteligente de templates
- Sugestão de templates baseado em contexto

### Fase 4: Gerenciamento de Conhecimento
- CRUD completo para Pessoas
- CRUD completo para Projetos
- Gerenciamento inteligente de Daily Notes
- Linkagem automática de menções

### Fase 5: Recursos MCP Avançados
- Resources navegáveis (`vault://structure`, `templates://by-folder`)
- Prompts pré-configurados
- Sampling para sugestões proativas

## Contribuindo

Para adicionar novos analyzers ou tools:

1. Criar novo analyzer em `src/mcp_obsidian/analyzers/`
2. Criar ToolHandler em `src/mcp_obsidian/tools.py`
3. Registrar tool em `src/mcp_obsidian/server.py`

## Estrutura do Código

```
src/mcp_obsidian/
├── __init__.py
├── server.py           # Servidor MCP principal
├── tools.py            # Tool handlers
├── obsidian.py         # Cliente API Obsidian
├── config.py           # Gerenciamento de configuração
├── analyzers/          # Módulos de análise
│   ├── structure.py    # Análise de estrutura do vault
│   ├── frontmatter.py  # Análise de frontmatter
│   └── __init__.py
└── knowledge/          # Gerenciadores de conhecimento (futuro)
    ├── people.py       # CRUD de pessoas
    ├── projects.py     # CRUD de projetos
    ├── daily.py        # Gerenciamento de daily notes
    └── __init__.py
```

## Testando

```bash
# Instalar em modo desenvolvimento
pip install -e .

# Configurar variáveis de ambiente
export OBSIDIAN_API_KEY="seu_token"
export OBSIDIAN_HOST="127.0.0.1"  # ou seu host remoto
export OBSIDIAN_PORT="27124"

# Executar servidor
python -m mcp_obsidian

# Testar com MCP Inspector
npx @modelcontextprotocol/inspector python -m mcp_obsidian
```

## API Remota

Para usar com API remota (como no exemplo `secondbrain.oihugudev.com.br`):

```bash
export OBSIDIAN_PROTOCOL="http"
export OBSIDIAN_HOST="secondbrain.oihugudev.com.br"
export OBSIDIAN_PORT="80"  # ou a porta apropriada
export OBSIDIAN_API_KEY="seu_token_aqui"
```

## Exemplo de Resposta

### obsidian_analyze_vault_structure

```json
{
  "root_folders": [
    "Arte Culinária",
    "Daily Notes",
    "Desenvolvimento",
    "People",
    "Projetos"
  ],
  "daily_notes": {
    "found": true,
    "folder": "Daily Notes",
    "pattern": "Daily Notes/YYYY/MM - Month Name/YYYY-MM-DD.md",
    "sample_sections": [
      "Resumo do Dia",
      "Projetos do Dia",
      "Registro de Ações (Tasks)"
    ],
    "frontmatter_fields": ["type", "tags", "date", "time", "mentions"]
  },
  "people": {
    "found": true,
    "folder": "People",
    "total_people": 28,
    "common_schema": {}
  },
  "projects": {
    "found": true,
    "folders": ["Projetos"],
    "hierarchy_pattern": "Company/Project"
  },
  "config_saved": true,
  "config_path": "/path/to/vault-config.json"
}
```


## Fase 4: Gerenciamento de Conhecimento ✅

Sistema completo de CRUD para Pessoas, Projetos e Daily Notes.

### 🆕 Tools Disponíveis (9 novos)

#### People Management

1. **`obsidian_create_person`** - Cria pessoa com frontmatter estruturado
2. **`obsidian_list_people`** - Lista pessoas com filtros (company, role, tags)
3. **`obsidian_update_person`** - Atualiza frontmatter ou adiciona conteúdo

#### Projects Management

4. **`obsidian_create_project`** - Cria projeto com hierarquia Company/Project
5. **`obsidian_list_projects`** - Lista projetos com filtros (company, status)
6. **`obsidian_list_companies`** - Lista todas as empresas/clientes

#### Daily Notes Management

7. **`obsidian_create_daily_note`** - Cria daily note com estrutura detectada
8. **`obsidian_append_to_daily`** - Adiciona em seção específica da daily
9. **`obsidian_get_recent_dailies`** - Busca daily notes recentes

### Schemas de Frontmatter

**Person:**
```yaml
name: Igor Curi
type: person
role: Colleague
company: BeSolution
email: igor@example.com
tags: [colleague, besolution]
```

**Project:**
```yaml
project: CNI - Chatbot
type: project
company: BeSolution
status: active
start_date: 2024-01-15
team: [Igor Curi, Amanda]
technologies: [Python, LeanML]
tags: [cni, ai]
```

**Daily Note:**
```yaml
type: daily-note
date: 2025-10-25
time: 14:30
tags: [work-log]
mentions: [Igor Curi]
```

### Workflows de Exemplo

**Adicionar pessoa e projeto:**
```
1. obsidian_create_person
   - name: "João Silva"
   - company: "Cliente X"
   
2. obsidian_create_project
   - name: "Novo Sistema"
   - company: "Cliente X"
   - team: ["João Silva"]
```

**Daily note com contexto:**
```
1. obsidian_create_daily_note
   - use_template: true
   
2. obsidian_append_to_daily
   - section: "Reuniões"
   - content: "- 14:00 - Reunião com [[João Silva]]"
```

Veja [PHASE4_IMPLEMENTATION.md](PHASE4_IMPLEMENTATION.md) para documentação completa.

