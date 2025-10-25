# MCP Obsidian - Intelligent Knowledge Manager

Um servidor MCP (Model Context Protocol) inteligente para Obsidian que entende automaticamente a estrutura do seu vault e fornece ferramentas contextuais para gerenciamento de conhecimento.

## 🆕 Novidades - Fase 1: Discovery & Introspection

### 🎯 O Que Mudou

Este fork adiciona **inteligência contextual** ao servidor MCP Obsidian. Agora o servidor pode:

- ✅ **Entender automaticamente** como seu vault está organizado
- ✅ **Detectar padrões** de Daily Notes, People, Projects
- ✅ **Analisar frontmatter** e sugerir melhorias
- ✅ **Fornecer contexto rico** sobre pastas e notas
- ✅ **Salvar configuração** para reutilização

### 🛠️ Novos Tools (4 tools adicionados)

#### 1. `obsidian_analyze_vault_structure`

Analisa a estrutura completa do vault e detecta padrões organizacionais.

```json
{
  "tool": "obsidian_analyze_vault_structure",
  "args": {
    "save_config": true
  }
}
```

**Retorna:**
- Estrutura de Daily Notes detectada
- Pasta de People e número de contatos
- Hierarquia de Projetos
- Schemas de frontmatter comuns
- Salva configuração em `vault-config.json`

#### 2. `obsidian_analyze_frontmatter`

Analisa padrões de frontmatter em uma pasta específica.

```json
{
  "tool": "obsidian_analyze_frontmatter",
  "args": {
    "folder_path": "People",
    "sample_size": 20
  }
}
```

**Retorna:**
- Campos comuns e suas frequências
- Tipos de dados esperados
- Campos faltantes em algumas notas
- Sugestões de padronização

#### 3. `obsidian_suggest_frontmatter`

Sugere melhorias de frontmatter para uma nota específica.

```json
{
  "tool": "obsidian_suggest_frontmatter",
  "args": {
    "note_path": "People/Igor Curi.md",
    "reference_folder": "People"
  }
}
```

**Retorna:**
- Campos recomendados para adicionar
- Inconsistências de tipo detectadas
- Exemplos de valores baseados em notas similares

#### 4. `obsidian_get_folder_context`

Fornece contexto rico sobre uma pasta.

```json
{
  "tool": "obsidian_get_folder_context",
  "args": {
    "folder_path": "Projetos/BeSolution"
  }
}
```

**Retorna:**
- Propósito da pasta (detectado automaticamente)
- Estatísticas (arquivos, subpastas)
- Padrões de frontmatter
- Amostra de arquivos

---

## 📦 Instalação

### Requisitos

- Python 3.11+
- Obsidian com plugin "Local REST API" instalado e configurado
- Token de API do Obsidian

### Instalação Rápida

```bash
# Clonar repositório
git clone https://github.com/seu-usuario/mcp-obsidian-fork.git
cd mcp-obsidian-fork

# Instalar dependências
pip install -e .

# Configurar variáveis de ambiente
export OBSIDIAN_API_KEY="seu_token_aqui"
export OBSIDIAN_HOST="127.0.0.1"  # ou seu host remoto
export OBSIDIAN_PORT="27124"
export OBSIDIAN_PROTOCOL="https"  # ou "http"
```

### Configuração para API Remota

```bash
export OBSIDIAN_PROTOCOL="http"
export OBSIDIAN_HOST="seu-dominio.com"
export OBSIDIAN_PORT="80"
export OBSIDIAN_API_KEY="seu_token_aqui"
```

---

## 🚀 Uso Rápido

### Primeiro Uso - Analisar Vault

```bash
# O servidor deve primeiro analisar seu vault
# Isso criará vault-config.json com toda estrutura detectada
```

No Claude Desktop ou via MCP:
```
Use o tool obsidian_analyze_vault_structure
```

### Exemplos de Uso

#### Entender contexto antes de trabalhar em uma pasta

```
Use obsidian_get_folder_context para "Projetos/BeSolution"
```

#### Padronizar frontmatter de uma pasta

```
1. Analise: obsidian_analyze_frontmatter --folder_path "People"
2. Para cada nota: obsidian_suggest_frontmatter
3. Aplique sugestões com obsidian_patch_content
```

#### Criar nova nota seguindo padrões

```
1. Obtenha contexto: obsidian_get_folder_context --folder_path "People"
2. Crie nota com frontmatter apropriado baseado no schema detectado
```

---

## 📁 Estrutura do Código

```
src/mcp_obsidian/
├── __init__.py
├── server.py              # Servidor MCP principal
├── tools.py               # Tool handlers (17 tools)
├── obsidian.py            # Cliente API Obsidian
├── config.py              # Sistema de configuração 🆕
├── analyzers/             # Módulos de análise 🆕
│   ├── __init__.py
│   ├── structure.py       # Análise de estrutura do vault
│   └── frontmatter.py     # Análise de frontmatter
└── knowledge/             # Gerenciadores (futuro)
    ├── __init__.py
    ├── people.py          # CRUD de pessoas
    ├── projects.py        # CRUD de projetos
    └── daily.py           # Gerenciamento de daily notes
```

---

## 🧪 Testes

```bash
# Executar suite de testes
python3 test_new_tools.py

# Executar testes detalhados
python3 test_detailed.py
```

**Resultados:** ✅ 4/4 testes passaram

Veja `TEST_REPORT.md` para relatório completo.

---

## 📊 O Que o Sistema Detectou (Exemplo Real)

**Vault testado:** http://secondbrain.oihugudev.com.br/

### Daily Notes
- **Padrão:** `Daily Notes/YYYY/MM - Month Name/YYYY-MM-DD.md`
- **Estrutura:** Hierárquica com pastas por semana (W##)
- **Seções:** Resumo do Dia, Projetos, Reuniões, Decisões, Notas Rápidas

### People
- **Total:** 28 pessoas
- **Frontmatter:** 0/28 (oportunidade de melhoria!)
- **Padrão de nome:** `{First Name} {Last Name}.md`

### Projetos
- **Hierarquia:** `Empresa/Projeto/Documento.md`
- **Empresas:** BeSolution (atual), Niteo (anterior)
- **Projetos:** CNI, Detran, Universidades, CellCoin, etc.
- **Frontmatter:** 0 (oportunidade de melhoria!)

---

## 🎯 Roadmap

### ✅ Fase 1: Discovery & Introspection (COMPLETA)
- Análise automática de estrutura
- Detecção de padrões de frontmatter
- Sistema de configuração
- Contexto rico de pastas

### 🔄 Fase 2: Navegação Semântica (Próxima)
- Busca por similaridade semântica
- Análise de relacionamentos entre notas
- Sugestão de links automáticos
- Embeddings com sentence-transformers

### 🔄 Fase 3: Sistema de Templates
- Detecção automática de templates
- Aplicação inteligente de templates
- Sugestão baseada em contexto

### 🔄 Fase 4: Gerenciamento de Conhecimento
- CRUD completo para Pessoas
- CRUD completo para Projetos
- Gerenciamento inteligente de Daily Notes
- Linkagem automática de menções

### 🔄 Fase 5: Recursos MCP Avançados
- Resources navegáveis (`vault://structure`)
- Prompts pré-configurados
- Sampling para sugestões proativas

---

## 📖 Documentação Adicional

- **[FEATURES.md](FEATURES.md)** - Detalhes de todas as funcionalidades
- **[TEST_REPORT.md](TEST_REPORT.md)** - Relatório completo de testes
- **[vault-config.json](vault-config.json)** - Exemplo de configuração

---

## 🤝 Contribuindo

Contribuições são bem-vindas!

### Áreas Prioritárias

1. **Fase 4:** Implementar CRUD de Pessoas e Projetos
2. **Fase 3:** Sistema de templates inteligentes
3. **Fase 2:** Busca semântica com embeddings
4. **Correções:** Bug cosmético em detecção de tipos

### Como Contribuir

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Add MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📝 Licença

MIT License - veja LICENSE para detalhes

---

## 🙏 Agradecimentos

- Projeto original: [coddingtonbear/obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api)
- Fork base MCP: [mcp-obsidian](https://github.com/shipurjan/mcp-obsidian)
- Anthropic pelo Model Context Protocol

---

## 📞 Suporte

- Issues: [GitHub Issues](https://github.com/seu-usuario/mcp-obsidian-fork/issues)
- Documentação: [Wiki](https://github.com/seu-usuario/mcp-obsidian-fork/wiki)

---

**Desenvolvido com ❤️ usando Claude Code**
