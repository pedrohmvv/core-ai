# Guia: Backup, Reingestão e Restore do Banco Vetorial no Railway

## Estratégia: local-first

A migração é feita em duas fases:

1. **Local (este guia, Passos 1–6):** reingestão com Google Embeddings no container Docker local que espelha o banco do Railway. O `.env` deve apontar para `localhost` durante esta fase.
2. **Railway (Passos 7–8):** substituição do banco em produção usando o dump gerado localmente.

Essa abordagem garante que o banco do Railway nunca fica em estado inconsistente durante a reingestão.

## Pré-requisitos

- Container Docker local rodando PostgreSQL + pgvector (espelho do Railway)
- `pg_dump` e `psql` instalados localmente (vem com PostgreSQL)
- `.env` atualizado com a nova `GOOGLE_API_KEY` da conta corporativa (`ai@coreai.com.br`)
- `.env` apontando para `localhost` (Docker), não para o Railway

---

## Passo 1 — Backup do banco atual (segurança)

Salva tudo antes de qualquer alteração. Use a DATABASE_URL do seu container Docker local:

```bash
# Docker local — valores do seu .env
export DATABASE_URL="postgresql://admin:adminpassword@localhost:5432/nutriai_db"

# Backup completo
pg_dump $DATABASE_URL \
  --no-acl \
  --no-owner \
  -f backup_huggingface_$(date +%Y%m%d).sql

# Confirmar que o backup foi gerado
ls -lh backup_huggingface_*.sql
```

Guarde esse arquivo — é o rollback completo caso algo dê errado.

---

## Passo 3 — Reingerir com Google Embeddings (notebook local)

Execute o notebook `notebooks/embeddings_migration.ipynb` gerado pelo Claude Code:

1. **Célula de validação** — confirma que `.env` aponta para `localhost`
2. **Backup automático** — salvo em `backups/backup_huggingface_YYYYMMDD.sql`
3. **DROP TABLE** — dropa `pg_langchain_vectors` no banco local
4. **Pipeline completo** — reingerir todos os PDFs com `text-multilingual-embedding-002`
5. **Validação semântica** — confirmar que similarity_search retorna resultados coerentes

> O notebook conecta ao container Docker local via `DB_URI_ASYNC` do `.env`.
> Nunca rode este notebook com `.env` apontando para o Railway.

---

## Passo 4 — Dump do novo banco vetorial (Google Embeddings 768d)

Após a reingestão, gere o dump da nova tabela:

```bash
# Dump apenas da tabela de vetores (mais leve e focado)
pg_dump $DATABASE_URL \
  --no-acl \
  --no-owner \
  --table=pg_langchain_vectors \
  -f dump_google_embeddings_768d_$(date +%Y%m%d).sql

# Verificar tamanho
ls -lh dump_google_embeddings_*.sql
```

---

## Passo 5 — Verificar resultado no banco local

Conecte ao container Docker local e confirme:

```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM pg_langchain_vectors;"
psql $DATABASE_URL -c "SELECT langchain_metadata->>'source', COUNT(*) FROM pg_langchain_vectors GROUP BY 1;"
```

A segunda query mostra quantos chunks foram gerados por PDF — útil para confirmar que todos os documentos foram reingeridos.

---

## Passo 6 — Restore do dump no Railway

Após validar o banco local, substitua o banco em produção:

```bash
# 1. Obter DATABASE_URL do Railway (dashboard → PostgreSQL → Variables)
export RAILWAY_URL="postgresql://user:password@host.railway.app:port/database"

# 2. Dropar a tabela antiga no Railway
psql $RAILWAY_URL -c "DROP TABLE IF EXISTS pg_langchain_vectors;"

# 3. Restaurar o dump gerado localmente
psql $RAILWAY_URL -f backups/dump_google_embeddings_768d_YYYYMMDD.sql

# 4. Confirmar
psql $RAILWAY_URL -c "SELECT COUNT(*) FROM pg_langchain_vectors;"
```

---

## Passo 7 — Deploy da API com novo modelo

Após confirmar que o banco do Railway está populado:

```bash
git add src/app/infrastructure/vector_store/embeddings.py
git add src/core/config.py
git commit -m "feat: migrar embeddings HuggingFace → Google Generative AI (768d)"
git push
```

O Railway faz o deploy automaticamente. Verifique no dashboard:
- **CPU Usage** deve cair de ~0.75 vCPU para ~0.05–0.1 vCPU em idle
- **Memory Usage** deve cair proporcionalmente

---

## Rollback (se necessário)

```bash
# Restaurar banco local
psql $DATABASE_URL -f backups/backup_huggingface_YYYYMMDD.sql

# Restaurar banco Railway
psql $RAILWAY_URL -f backups/backup_huggingface_YYYYMMDD.sql

# Reverter código
git revert HEAD
git push
```

---

## Checklist final

### Fase local
- [ ] `.env` apontando para `localhost` (Docker)
- [ ] `.env` atualizado com nova `GOOGLE_API_KEY` (ai@coreai.com.br)
- [ ] Notebook `embeddings_migration.ipynb` executado com sucesso
- [ ] Backup salvo em `backups/backup_huggingface_YYYYMMDD.sql`
- [ ] `SELECT COUNT(*)` confirma chunks no banco local
- [ ] Validação semântica retorna resultados coerentes
- [ ] Dump salvo em `backups/dump_google_embeddings_768d_YYYYMMDD.sql`

### Fase Railway
- [ ] Railway: variável `GOOGLE_API_KEY` atualizada
- [ ] Dump restaurado no banco do Railway
- [ ] `SELECT COUNT(*)` confirma chunks no Railway
- [ ] `embeddings.py` e `config.py` atualizados
- [ ] Deploy realizado (`git push`)
- [ ] CPU/RAM do Railway em queda confirmada no dashboard