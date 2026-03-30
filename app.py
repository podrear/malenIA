import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import time

# --- Configuration de la page ---
st.set_page_config(page_title="IA Émotionnelle v5", page_icon="🧠", layout="wide")

# On s'assure que les dossiers et modules locaux sont accessibles
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chat_engine import ChatEngine
from rag.memories import FALSE_MEMORIES

# --- Initialisation de l'état ---
if "engine" not in st.session_state:
    st.session_state.engine = ChatEngine(enable_sentiment=True, enable_rag=True)
    # Mode test : très réactif pour les démos
    if st.session_state.engine.emotion_engine:
        st.session_state.engine.emotion_engine.IDLE_THRESHOLD = 15  
        st.session_state.engine.emotion_engine.SPONTANEOUS_CHANCE = 0.95
    st.session_state.messages = []
    st.session_state.is_generating = False
    st.session_state.pending_prompt = None

engine = st.session_state.engine

# --- Auto-refresh pour actualiser les jauges et capter les spontanés ---
if not st.session_state.is_generating:
    count = st_autorefresh(interval=2000, limit=None, key="emotion_autorefresh")

# Autoriser l'IA à parler d'elle-même dans ce thread/cycle
if getattr(st.session_state, "is_generating", False) == False:
    spontaneous = engine.get_spontaneous_response()
    if spontaneous:
        msg, emo = spontaneous
        st.session_state.messages.append({"role": "assistant", "content": msg})
        # Le rerun va tout afficher

em_state = engine.emotion_engine

# --- Composants Graphiques (Plotly) ---
def create_gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        number = {'valueformat': '.2f'},
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [-1, 1], 'tickwidth': 1, 'tickcolor': "darkgray"},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [-1, -0.3], 'color': 'rgba(255, 0, 0, 0.1)'},
                {'range': [-0.3, 0.3], 'color': 'rgba(200, 200, 200, 0.1)'},
                {'range': [0.3, 1], 'color': 'rgba(0, 255, 0, 0.1)'}
            ],
            'threshold': {
                'line': {'color': color, 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    fig.update_layout(height=180, margin=dict(l=10, r=10, t=30, b=10))
    return fig

def plot_trajectory(trajectory):
    if not trajectory:
         return go.Figure()
    
    lengths = len(trajectory)
    x = list(range(lengths))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=[t.v if hasattr(t, 'v') else t.get('v', 0) for t in trajectory], mode='lines', name='Valence', line=dict(color='royalblue', width=2)))
    fig.add_trace(go.Scatter(x=x, y=[t.e if hasattr(t, 'e') else t.get('e', 0) for t in trajectory], mode='lines', name='Énergie', line=dict(color='crimson', width=2)))
    fig.add_trace(go.Scatter(x=x, y=[t.s if hasattr(t, 's') else t.get('s', 0) for t in trajectory], mode='lines', name='Social', line=dict(color='mediumpurple', width=2)))
    fig.add_trace(go.Scatter(x=x, y=[t.d if hasattr(t, 'd') else t.get('d', 0) for t in trajectory], mode='lines', name='Dominance', line=dict(color='darkorange', width=2)))
    
    fig.update_layout(
        title="Trajectoire Émotionnelle (30 derniers snapshots)",
        xaxis_title="Temps",
        yaxis_title="Intensité (-1 à 1)",
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_range=[-1.05, 1.05],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# --- Layout Principal ---
col_dash, col_chat = st.columns([1, 1.2])

with col_dash:
    st.header("🧠 Météo Interne")
    
    if em_state:
        # Infos générales
        st.markdown(f"#### Émotions Actives : {em_state.get_combined_display()}")
        
        intensities_str = " | ".join([f"**{k}**: {v:.0%}" for k,v in em_state.emotion_intensities.items()])
        st.info(f"**Intensités relatives** : {intensities_str}")
        
        idle = time.time() - em_state._last_interaction
        st.caption(f"Spontanés : {em_state._spontaneous_count} | Inactivité : {idle:.0f}s / {em_state.IDLE_THRESHOLD}s")
        
        # Jauges
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(create_gauge(em_state.v, "Valence (Joie/Tristesse)", "royalblue"), use_container_width=True)
            st.plotly_chart(create_gauge(em_state.s, "Social (Connexion/Solitude)", "mediumpurple"), use_container_width=True)
        with c2:
            st.plotly_chart(create_gauge(em_state.e, "Énergie (Panique/Calme)", "crimson"), use_container_width=True)
            st.plotly_chart(create_gauge(em_state.d, "Dominance (Contrôle/Soumis)", "darkorange"), use_container_width=True)
            
        # Graphique temps réel
        st.plotly_chart(plot_trajectory(em_state.trajectory), use_container_width=True)
        
        # Outils RAG Memory
        with st.expander("🛠️ Outils & Mémoire", expanded=False):
            if st.button("🧠 Injecter Faux Souvenirs"):
                if engine._store:
                    count = engine._store.inject_false_memories(FALSE_MEMORIES)
                    st.success(f"✅ {count} souvenirs humains injectés dans ChromaDB !")
                else:
                    st.error("RAG désactivé.")
            if st.button("🧹 Vider la mémoire RAG"):
                if engine._store:
                    engine._store.clear()
                    st.success("Mémoire vidée.")
    else:
        st.warning("Moteur émotionnel désactivé.")

with col_chat:
    st.header("💬 Interface de Discussion")
    
    chat_container = st.container(height=650)
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Dites quelque chose à l'IA...", disabled=st.session_state.is_generating):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.pending_prompt = prompt
        st.session_state.is_generating = True
        st.rerun()

    # Si une génération est en cours
    if st.session_state.is_generating and st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        
        # Empêche la réponse spontanée immédiate
        if engine.emotion_engine:
            engine.emotion_engine.touch()

        # Phase assistant
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Je ressens et je réfléchis..."):
                    # On appelle send_message (qui va faire le RAG + Moteur d'émotion + Inference)
                    response_text, sentiment_result, ai_emotion, rag_sources = engine.send_message(prompt)
                    st.markdown(response_text)
                    if rag_sources:
                        with st.expander("📖 Ce que cela me rappelle..."):
                            for src in rag_sources:
                                st.write(f"- _{src['text']}_")
            
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            # Libération du lock
            st.session_state.is_generating = False
            st.session_state.pending_prompt = None
            st.rerun()
