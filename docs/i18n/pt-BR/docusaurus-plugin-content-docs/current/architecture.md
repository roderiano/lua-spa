---
sidebar_position: 3
---

# Visão Geral da Arquitetura

Entenda como Lua SPA funciona nos bastidores.

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     Navegador (Cliente)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Runtime JS (runtime_assets.py)                       │  │
│  │ - Gerenciamento de estado                            │  │
│  │ - Manipulação de eventos                             │  │
│  │ - DOM diffing                                        │  │
│  │ - Ciclo de vida de componentes                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ HTTP / WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend Python                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ SpaFramework (framework.py)                          │  │
│  │  - Orquestra renderização e servindo                │  │
│  │  - Gerencia ciclo de vida de componentes             │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────┬───────────┼───────────┬─────────────────┐  │
│  │            │           │           │                 │  │
│  ▼            ▼           ▼           ▼                 ▼  │
│ Loader    Scope       Renderer    CodeGen          Server   │
│(loader.py)(scope.py) (renderer.py)(codegen.py)  (server.py) │
│  - Carrega - Executa  - Constrói  - Gera        - HTTP     │
│    .lspa    Python     HTML        JavaScript    - Rota    │
│  - Analisa - Extrai   - Insere    - Injeta      - Serve   │
│    importa context    estado      runtime                   │
└─────────────────────────────────────────────────────────────┘
```

## Fluxo de Solicitação/Resposta

### Carregamento Inicial da Página

```
1. Navegador requisita GET /
         │
         ▼
2. Servidor (server.py)
   - Carrega configuração de spa.config.json
   - Cria instância SpaFramework
         │
         ▼
3. SpaFramework.render()
   - Carrega componente de entrada
   - Extrai bloco python_block
         │
         ▼
4. Escopo (scope.py)
   - Executa código Python do componente
   - Extrai callables context() e client()
   - Normaliza definições de estado e métodos
         │
         ▼
5. Renderizador (renderer.py)
   - Chama context(props) para obter dados do servidor
   - Interpola variáveis no template
   - Aplica diretivas v-if, v-for
   - Retorna HTML renderizado
         │
         ▼
6. Gerador de Código (codegen.py)
   - Extrai especificações do cliente
   - Gera classe JavaScript
   - Injeta como tag <script>
         │
         ▼
7. Resposta HTML
   - HTML completo + JS incorporado + CSS
   - Inclui Runtime JS (runtime_assets.py)
```

## Ciclo de Vida do Componente

Um componente passa por vários estágios durante sua vida útil:

1. **Parsing** (loader.py) - Dividir em blocos de Python, template e importações
2. **Execução** (scope.py) - Executar bloco Python e extrair especificações
3. **Renderização** (renderer.py) - Mesclar dados com template
4. **Geração de Código** (codegen.py) - Gerar JavaScript para cliente
5. **Hidratação** (Runtime JS) - Inicializar no navegador com estado

## Responsabilidades dos Módulos

### `framework.py` - Classe SpaFramework

**Propósito**: Orquestrador principal do sistema.

**Responsabilidades**:
- Carrega componentes .lspa
- Coordena pipeline de renderização
- Gera código do cliente
- Injeta runtime

### `loader.py` - Classe ComponentLoader

**Propósito**: Analisa e carrega arquivos .lspa.

**Responsabilidades**:
- Analisa estrutura de arquivo .lspa
- Extrai bloco python, template, importações
- Carrega componentes importados recursivamente
- Armazena em cache componentes carregados

### `scope.py` - Execução de Escopo de Componente

**Propósito**: Executa código Python em escopo isolado.

**Responsabilidades**:
- Executa Python do componente com segurança
- Extrai interfaces chamáveis
- Valida especificações do cliente
- Normaliza definições de estado e método

### `renderer.py` - Renderização de Template

**Propósito**: Renderiza templates com dados.

**Responsabilidades**:
- Interpolação de variáveis de template
- Processamento de diretivas
- Serialização de estado
- Geração HTML

### `codegen.py` - Geração de Código JavaScript

**Propósito**: Gera JavaScript do lado do cliente.

**Responsabilidades**:
- Gera classe JavaScript a partir de especificações
- Cria código de gerenciamento de estado
- Cria dispatch de métodos
- Cria código de ligação de eventos

## Fluxo de Gerenciamento de Estado

```
Props do Componente
      │
      ▼
┌──────────────────┐
│ Servidor Renderiza│
│ HTML com estado  │
└──────────────────┘
      │
      ▼
┌──────────────────────────────────┐
│ Navegador recebe HTML            │
│ Hidrata JS com estado            │
│ Anexa ouvintes de eventos        │
└──────────────────────────────────┘
      │
      ▼
Interação do usuário (clique, entrada, etc.)
      │
      ▼
┌──────────────────────────────┐
│ Método executa               │
│ Retorna objeto de operação   │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│ Operação se aplica           │
│ ao estado em memória         │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│ Componente re-renderiza      │
│ com novo estado              │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│ Algoritmo de difusão de DOM  │
│ compara HTML antigo vs novo  │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│ Atualizações mínimas de DOM  │
│ aplicadas à página           │
└──────────────────────────────┘
```

## Próximos Passos

- [Framework](./api/framework.md) - Documentação detalhada de SpaFramework
- [Componentes](./components/index.md) - Criar guia de componentes
