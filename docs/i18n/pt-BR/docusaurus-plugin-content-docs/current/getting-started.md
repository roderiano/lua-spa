---
sidebar_position: 2
---

# Começando

Aprenda como configurar Lua SPA e criar seu primeiro componente.

## Pré-requisitos

- **Python 3.11+**
- **Poetry** (para gerenciamento de dependências)
- Um navegador web moderno

## Instalação

### 1. Clone e Instale

```bash
git clone https://github.com/lua-spa/lua-spa.git
cd lua-spa
poetry install
```

### 2. Execute o Servidor de Desenvolvimento

```bash
poetry run lua-spa
```

Você deve ver uma saída como:

```
Iniciando servidor de desenvolvimento em http://127.0.0.1:8000
Pressione Ctrl+C para parar o servidor
```

### 3. Abra seu Navegador

Navegue até `http://127.0.0.1:8000` e você deve ver o exemplo do Counter.

## Estrutura do Projeto

O framework lê sua aplicação do diretório `lua_template/`:

```
lua_template/
├── spa.config.json          # Configuração da aplicação
├── index.lspa              # Template HTML raiz
└── components/             # Seus componentes
    ├── App.lspa
    └── Counter.lspa
```

## Entendendo spa.config.json

O arquivo `spa.config.json` contém configuração global da aplicação:

```json
{
  "entry_component": "App",
  "mount_id": "app",
  "initial_props": {},
  "server": {
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

**Campos:**
- `entry_component` - Componente raiz a renderizar
- `mount_id` - ID do DOM onde a aplicação monta
- `initial_props` - Props padrão passadas ao componente raiz
- `server` - Configuração de host e porta

## Seu Primeiro Componente

Crie `lua_template/components/Counter.lspa`:

```html
<python>
from lua_spa.types import ClientMethods

class Component:
    def context(self, props):
        return {"label": "Contador"}
    
    def client(self):
        class CounterClient(ClientMethods):
            start = 0
            
            class CountState:
                name = "count"
                from_prop = "start"
                default = 0
                cast = "int"
            
            State = [CountState]
            Methods = ["increment", "reset"]
            
            def increment(self):
                return self.add("count", 1)
            
            def reset(self):
                return self.set("count", 0)
        
        return CounterClient()
</python>

<template>
  <div>
    <h1>{{ label }}</h1>
    <p>Contagem: <strong>{{ count }}</strong></p>
    
    <button @click="increment">+1</button>
    <button @click="reset">Resetar</button>
  </div>
</template>
```

### Quebrando em Partes

1. **Bloco `<python>`**: Define lógica do servidor e cliente
   - `context(props)` - Dados do lado do servidor para renderização
   - `client()` - Retorna classe de componente do cliente

2. **Definição de Estado**:
   - `name` - Nome da variável no template
   - `from_prop` - Inicializa a partir de uma prop
   - `default` - Valor inicial padrão
   - `cast` - Coerção de tipo (`"int"`, `"str"`, `"bool"`, `"float"`, `"raw"`)

3. **Métodos**: Lista de nomes de métodos que podem ser chamados no cliente
   - `increment()` - Retorna operação a executar
   - `reset()` - Retorna operação a executar

4. **Bloco `<template>`**: Sintaxe de template semelhante a Vue
   - `{{ }}` - Interpolação de variáveis
   - `@click` - Ligação de eventos
   - `v-if`, `v-for`, etc. - Diretivas Vue

## Renderização e Hidratação

Quando você inicia o servidor:

1. **Servidor**: Renderiza o componente para HTML usando dados de `context()`
2. **Cliente**: Hidrata o HTML com JavaScript de `client()`
3. **Interação**: Eventos do usuário disparam mudanças de estado no cliente
4. **Atualização**: DOM se atualiza automaticamente com base em mudanças de estado

## Próximos Passos

- Aprenda [Conceitos de Componentes](./components/index.md)
- Explore [Gerenciamento de Estado](./components/state.md)
- Leia a [API do Framework](./api/framework.md)

## Solução de Problemas

### Porta já em uso

Altere a porta em `spa.config.json`:

```json
"server": {
  "port": 8001
}
```

### Componente não está sendo renderizado

1. Verifique que o arquivo de componente existe em `lua_template/components/`
2. Certifique-se de que o nome do arquivo corresponde à importação (sensível a maiúsculas)
3. Verifique o terminal para erros de sintaxe Python no componente

### Mudanças de estado não se refletem

Certifique-se de que seu método retorna um dicionário de operação:

```python
def increment(self):
    return self.add("count", 1)  # Retorna operação
```
