from __future__ import annotations

import os
import shutil
from pathlib import Path


def _install_hosted_secrets() -> None:
    """Disponibiliza no Streamlit o arquivo secreto montado pela hospedagem."""
    source_name = os.environ.get("APP_AUTH_SECRETS_FILE", "").strip()
    if not source_name:
        return

    source = Path(source_name)
    if not source.is_file():
        return

    target = Path(__file__).parent / ".streamlit" / "secrets.toml"
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(source, target)


_install_hosted_secrets()

import streamlit as st


def _secret(name: str, default: str = "") -> str:
    """Lê configuração do ambiente ou dos secrets sem expô-la na interface."""
    try:
        value = st.secrets.get(name, os.environ.get(name, default))
    except FileNotFoundError:
        value = os.environ.get(name, default)
    return str(value).strip()


for _setting in ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_VECTOR_STORE_ID", "APP_DATA_DIR"):
    _value = _secret(_setting)
    if _value:
        os.environ[_setting] = _value

from access_control import (  # noqa: E402
    add_extra_questions,
    consume_question,
    grant_access,
    initialize as initialize_access,
    list_users,
    revoke_access,
    user_status,
)
from ingest import DOCS_DIR, delete_manual, index_pdf  # noqa: E402
from rag import answer, indexed_sources, openai_status  # noqa: E402


st.set_page_config(page_title="Assistente de Pitometria", page_icon="💧", layout="wide")
initialize_access()

ADMIN_EMAIL = _secret("APP_ADMIN_EMAIL").lower()
ADMIN_DAILY_LIMIT = int(_secret("APP_ADMIN_DAILY_LIMIT", "100"))

if not ADMIN_EMAIL:
    st.error("O portal ainda não tem um administrador configurado.")
    st.caption("Defina APP_ADMIN_EMAIL nos secrets da hospedagem antes de liberar o acesso.")
    st.stop()

if not st.user.is_logged_in:
    st.title("Assistente técnico de Pitometria e Macromedição")
    st.write("Entre com sua conta para consultar os manuais autorizados.")
    if st.button("Entrar", type="primary", icon=":material/login:"):
        st.login("google")
    st.stop()

email = str(getattr(st.user, "email", "")).strip().lower()
if not email:
    st.error("O provedor de login não informou seu e-mail. Use uma conta que compartilhe o e-mail.")
    st.stop()

is_admin = email == ADMIN_EMAIL
if is_admin and user_status(email) is None:
    grant_access(email, ADMIN_DAILY_LIMIT)

status = user_status(email)
if not is_admin and (not status or not status["enabled"]):
    st.title("Acesso pendente")
    st.info("Seu e-mail ainda não foi autorizado para consultar os manuais.")
    st.caption(f"E-mail identificado: {email}")
    st.stop()

st.session_state.setdefault("messages", [])
st.title("Assistente técnico de Pitometria e Macromedição")
st.caption("Todos os manuais são pesquisados pela IA da OpenAI. Cada pergunta consome uma consulta diária.")


def _show_sources(sources: list[dict], title: str) -> None:
    if not sources:
        return
    with st.expander(title):
        for source in sources:
            metadata = source["metadata"]
            st.markdown(f"**{metadata['source']} — página {metadata['page']}**")
            st.caption(source["text"])


with st.sidebar:
    st.header("Sua sessão")
    st.caption(email)
    if st.button("Sair", icon=":material/logout:"):
        st.logout()

    manuals = indexed_sources()
    if manuals:
        selected_manuals = st.multiselect(
            "Manuais a consultar", options=manuals, default=manuals, key="selected_manuals"
        )
    else:
        selected_manuals = []
        st.warning("Nenhum manual foi indexado ainda.")

    status = user_status(email)
    if status:
        st.caption(f"Consultas com IA restantes hoje: {status['remaining']}")

    if is_admin:
        st.divider()
        st.header("Administração")

        admin_status = user_status(ADMIN_EMAIL) or {"daily_limit": ADMIN_DAILY_LIMIT}
        with st.expander("Aumentar meu limite de consultas"):
            with st.form("admin_daily_limit_form"):
                admin_daily_limit = st.number_input(
                    "Consultas com IA por dia",
                    min_value=1,
                    max_value=10_000,
                    value=min(10_000, max(1, int(admin_status["daily_limit"]))),
                )
                admin_limit_submitted = st.form_submit_button("Salvar meu limite")
            if admin_limit_submitted:
                try:
                    grant_access(ADMIN_EMAIL, int(admin_daily_limit))
                    st.success("Seu limite diário foi atualizado.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

        with st.expander("Indexar manuais"):
            uploaded_files = st.file_uploader(
                "Adicionar manuais PDF", type="pdf", accept_multiple_files=True, key="admin_uploads"
            )
            if st.button("Indexar manuais enviados", disabled=not uploaded_files, icon=":material/upload_file:"):
                pending_files = [item for item in uploaded_files if item.name not in manuals]
                if not pending_files:
                    st.info("Todos os PDFs selecionados já estão indexados.")
                else:
                    DOCS_DIR.mkdir(parents=True, exist_ok=True)
                    progress = st.progress(0, text="Enviando manuais para a IA...")
                    for position, uploaded in enumerate(pending_files, start=1):
                        destination = DOCS_DIR / uploaded.name
                        with destination.open("wb") as output:
                            output.write(uploaded.getbuffer())
                        index_pdf(destination)
                        progress.progress(
                            position / len(pending_files),
                            text=f"{uploaded.name}: manual indexado pela IA.",
                        )
                    st.success("Manuais indexados pela IA e prontos para consulta.")
                    st.rerun()

        with st.expander("Excluir manual indexado"):
            if manuals:
                manual_to_delete = st.selectbox(
                    "Manual a excluir", manuals, key="manual_to_delete"
                )
                confirm_delete = st.checkbox(
                    f"Confirmo a exclusão permanente de {manual_to_delete}",
                    key="confirm_manual_delete",
                )
                if st.button(
                    "Excluir manual",
                    disabled=not confirm_delete,
                    icon=":material/delete:",
                ):
                    try:
                        deletion_warning = delete_manual(manual_to_delete)
                        if deletion_warning:
                            st.warning(deletion_warning)
                        else:
                            st.success(f"{manual_to_delete} foi excluído do Vector Store e do armazenamento local.")
                        st.rerun()
                    except Exception:
                        st.error("Não foi possível excluir o manual. Ele pode continuar disponível até a conclusão da remoção.")
            else:
                st.info("Não há manuais indexados para excluir.")

        with st.expander("Liberar acesso e cotas"):
            with st.form("grant_access_form"):
                invited_email = st.text_input("E-mail da pessoa autorizada")
                daily_limit = st.number_input("Consultas com IA por dia", min_value=1, max_value=10_000, value=10)
                grant_submitted = st.form_submit_button("Salvar autorização", icon=":material/person_add:")
            if grant_submitted:
                try:
                    grant_access(invited_email, int(daily_limit))
                    st.success("Acesso autorizado.")
                except ValueError as exc:
                    st.error(str(exc))

            users = list_users()
            if users:
                st.dataframe(users, hide_index=True, height=220)
                user_emails = [user["E-mail"] for user in users if user["E-mail"] != ADMIN_EMAIL]
                if user_emails:
                    selected_user = st.selectbox("Pessoa", user_emails, key="managed_user")
                    extra = st.number_input("Perguntas extras", min_value=1, max_value=10_000, value=1)
                    if st.button("Liberar extras", icon=":material/add:"):
                        try:
                            add_extra_questions(selected_user, int(extra))
                            st.success("Perguntas extras liberadas.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                    if st.button("Revogar acesso", icon=":material/block:"):
                        revoke_access(selected_user)
                        st.success("Acesso revogado.")
                        st.rerun()

if st.button("Limpar conversa", icon=":material/delete_sweep:"):
    st.session_state.messages = []
    st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        _show_sources(message.get("sources", []), message.get("sources_title", "Trechos usados pela IA"))

question = st.chat_input("Pergunte sobre os manuais indexados")
if question:
    if not selected_manuals:
        st.warning("Selecione pelo menos um manual antes de fazer uma pergunta.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            updated_status = consume_question(email)
        except PermissionError as exc:
            st.error(str(exc))
            st.stop()
        ready, message = openai_status()
        if not ready:
            st.error("A IA não está disponível no momento.")
            st.caption(message)
            st.stop()
        with st.spinner("Consultando os manuais com IA..."):
            history = st.session_state.messages[:-1][-6:]
            try:
                response, sources = answer(question, history, selected_sources=selected_manuals)
            except Exception:
                response = "Não foi possível consultar a IA agora. Tente novamente em alguns instantes."
                sources = []
        st.markdown(response)
        st.caption(f"Consultas com IA restantes hoje: {updated_status['remaining']}")

    st.session_state.messages.append(
        {"role": "assistant", "content": response, "sources": [], "sources_title": ""}
    )
