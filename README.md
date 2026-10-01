# ExportAI

Plataforma de inteligência e análise para exportação. Este repositório centraliza a documentação geral do sistema, a API principal do backend e a navegação entre os módulos do projeto.

---

## 🔗 Ecossistema do Projeto

O **ExportAI** é composto por serviços e módulos independentes:

| Módulo | Descrição | Repositório |
| :--- | :--- | :--- |
| ⚡ **Backend Principal** | API REST em FastAPI e Health Checks | *(Este repositório)* |
| 📊 **Módulo de Vendas** | Análise, métricas e histórico de vendas | [GustavoSchwabeRazera/ModuloVendas](https://github.com/GustavoSchwabeRazera/ModuloVendas) |
| 🔍 **Módulo de Diagnóstico** | Diagnóstico do perfil exportador e scoring | [GustavoSchwabeRazera/ModuloDiagnostico](https://github.com/GustavoSchwabeRazera/ModuloDiagnostico) |

---

## 🚀 ExportAI Backend

Estrutura FastAPI principal do projeto.

### ⚙️ Instalar dependências

No PowerShell, a partir da pasta `backend`:

```powershell
python -m pip install -r requirements.txt
