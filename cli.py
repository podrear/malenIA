"""
Interface CLI interactive pour le chatbot IA.
"""

import logging
import sys
import threading
import time
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

from chat_engine import ChatEngine


console = Console()
logger = logging.getLogger(__name__)


HELP_TEXT = """
[bold cyan]Commandes disponibles :[/]
  [green]/help[/]             — Affiche cette aide
  [green]/quit[/]             — Quitte le chatbot
  [green]/reset[/]            — Réinitialise la conversation
  [green]/index[/]            — Indexe les documents du dossier ./documents/
  [green]/index <dossier>[/]  — Indexe les documents d'un dossier spécifique
  [green]/inject_memories[/]  — Injecte les faux souvenirs de l'IA dans l'index RAG
  [green]/status[/]           — Affiche le nombre de documents indexés
  [green]/clear[/]            — Vide l'index RAG
  [green]/mood[/]             — Affiche l'état émotionnel complet de l'IA
  [green]/trajectory[/]       — Affiche la trajectoire émotionnelle récente
"""


def display_banner():
    """Affiche la bannière de démarrage."""
    banner = Text()
    banner.append("🤖 ", style="bold")
    banner.append("Chatbot IA Local", style="bold bright_cyan")
    banner.append(" — ", style="dim")
    banner.append("Sentiments + RAG + Émotions v5", style="bold magenta")

    console.print()
    console.print(Panel(banner, border_style="bright_cyan", padding=(1, 2)))
    console.print("[dim]Tapez /help pour voir les commandes disponibles.[/]")
    console.print()


def render_spectrum_bar(label: str, value: float, icons: tuple, trend: str = "➡️", width: int = 30) -> str:
    """Génère une barre bipolaire [  Low <--- ● ---> High  ]."""
    left_icon, right_icon = icons
    pos = int(((value + 1) / 2) * width)
    pos = max(0, min(width, pos))

    bar = ["─"] * (width + 1)
    bar[pos] = "●"
    bar_str = "".join(bar)

    color = "cyan" if value < -0.2 else ("yellow" if value > 0.2 else "white")
    if "Valence" in label:
        color = "red" if value < -0.3 else ("bright_green" if value > 0.3 else "white")
    elif "Énergie" in label:
        color = "blue" if value < -0.3 else ("bright_red" if value > 0.3 else "white")
    elif "Social" in label:
        color = "grey37" if value < -0.3 else ("medium_purple1" if value > 0.3 else "white")
    elif "Dominance" in label:
        color = "dark_orange" if value < -0.3 else ("gold1" if value > 0.3 else "white")

    return f"  [bold]{label:8}[/] {left_icon} [dim grey37]{bar_str}[/] {right_icon} [bold {color}]{value:+.1f}[/] [dim]{trend}[/]"


def display_emotions(user_sentiment: dict | None, ai_emotion: dict | None):
    """Affiche les badges de sentiments et les spectres de l'IA."""
    if user_sentiment and ai_emotion:
        console.print(
            f"  [dim]👤 Vous semblez :[/] [{user_sentiment['color']}]{user_sentiment['display']}[/]"
        )

        spectra = ai_emotion.get("spectra", [])
        if spectra:
            console.print("  [dim]🤖 Spectres de l'IA :[/]")
            for s in spectra:
                console.print(f"     {render_spectrum_bar(s['name'], s['value'], s['icons'], trend=s.get('trend', '➡️'))}")

        # v4 : afficher le pattern de trajectoire si non stable
        pattern = ai_emotion.get("trajectory_pattern", {})
        if pattern and pattern.get("type") not in ("stable", "", None):
            ptype = pattern["type"]
            style_map = {
                "crash": "bold red",
                "recovery": "bold green",
                "stagnation": "bold yellow",
                "oscillation": "bold magenta",
            }
            style = style_map.get(ptype, "dim")
            console.print(f"  [dim]📈 Trajectoire :[/] [{style}]{ptype.upper()}[/] [dim]— {pattern.get('description', '')}[/]")


def display_sources(sources: list[dict]):
    """Affiche les sources RAG utilisées."""
    if sources:
        console.print()
        console.print("  [dim italic]📚 Sources utilisées :[/]")
        for s in sources:
            console.print(
                f"    [dim]• {s['source']} (pertinence: {s['score']:.0%})[/]"
            )


def display_mood(engine: ChatEngine):
    """Affiche l'état émotionnel complet de l'IA (commande /mood)."""
    em = engine.emotion_engine
    if not em:
        console.print("[yellow]Moteur émotionnel désactivé.[/]")
        return

    console.print(Panel(
        f"[bold]Émotions actives :[/] {em.get_combined_display()}\n"
        f"[bold]Position :[/] V={em.v:+.2f}  E={em.e:+.2f}  S={em.s:+.2f}  D={em.d:+.2f}\n"
        f"[bold]Momentum :[/] dV={em._dv:+.3f}  dE={em._de:+.3f}  dS={em._ds:+.3f}  dD={em._dd:+.3f}\n"
        f"[bold]Intensités :[/] {em.emotion_intensities}\n"
        f"[bold]Trajectoire :[/] {em.get_trajectory_pattern()}\n"
        f"[bold]Snapshots :[/] {len(em.trajectory)}/{em.TRAJECTORY_SIZE}\n"
        f"[bold]Idle :[/] {time.time() - em._last_interaction:.0f}s / {em.IDLE_THRESHOLD}s\n"
        f"[bold]Spontanés :[/] count={em._spontaneous_count}\n"
        f"───────────────────────────────\n"
        f"[bold]🐣 Âge :[/] {em.get_age_display()}\n"
        f"[bold]💬 Interactions :[/] {em.total_interactions}\n"
        f"[bold]🔄 Session :[/] #{em.total_sessions}",
        title="[bold cyan]🧠 État Émotionnel v5[/]",
        border_style="cyan",
    ))


def display_trajectory(engine: ChatEngine):
    """Affiche la trajectoire émotionnelle récente (commande /trajectory)."""
    em = engine.emotion_engine
    if not em:
        console.print("[yellow]Moteur émotionnel désactivé.[/]")
        return

    if not em.trajectory:
        console.print("[dim]Aucune trajectoire enregistrée.[/]")
        return

    lines = []
    for i, snap in enumerate(em.trajectory):
        age = time.time() - snap.timestamp
        emotions_str = ", ".join(snap.emotions)
        lines.append(
            f"  [dim]#{i:02d}[/] [{age:6.0f}s ago] "
            f"V={snap.v:+.2f} E={snap.e:+.2f} S={snap.s:+.2f} D={snap.d:+.2f} "
            f"[dim]→[/] {emotions_str} "
            f"[dim italic]({snap.trigger})[/]"
        )

    console.print(Panel(
        "\n".join(lines),
        title="[bold cyan]📈 Trajectoire Émotionnelle[/]",
        border_style="cyan",
    ))


def handle_command(command: str, engine: ChatEngine) -> bool:
    """
    Gère les commandes spéciales.
    Returns True si le programme doit continuer, False pour quitter.
    """
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd == "/quit":
        # Sauvegarder l'état émotionnel avant de quitter
        if engine.emotion_engine:
            engine.emotion_engine.save_state()
            console.print("[dim]💾 État émotionnel sauvegardé.[/]")
        console.print("\n[bright_cyan]👋 À bientôt ![/]\n")
        return False

    elif cmd == "/help":
        console.print(HELP_TEXT)

    elif cmd == "/reset":
        engine.reset()
        console.print("[yellow]🔄 Conversation réinitialisée.[/]\n")

    elif cmd == "/index":
        directory = parts[1] if len(parts) > 1 else None
        console.print("[dim]📂 Indexation des documents en cours...[/]")
        count = engine.index_documents(directory)
        console.print(f"[green]✅ {count} chunks indexés.[/]\n")

    elif cmd == "/inject_memories":
        from rag.memories import FALSE_MEMORIES
        if engine._store:
            console.print("[dim]🧠 Injection de la mémoire fondatrice (faux souvenirs)...[/]")
            count = engine._store.inject_false_memories(FALSE_MEMORIES)
            console.print(f"[green]✅ {count} souvenirs incarnés avec succès.[/]\n")
        else:
            console.print("[red]❌ RAG désactivé. Impossible d'injecter les souvenirs.[/]\n")

    elif cmd == "/status":
        count = engine.rag_doc_count
        console.print(f"[cyan]📊 {count} chunks dans l'index RAG.[/]\n")

    elif cmd == "/clear":
        engine.clear_index()
        console.print("[yellow]🗑️  Index RAG vidé.[/]\n")

    elif cmd == "/mood":
        display_mood(engine)

    elif cmd == "/trajectory":
        display_trajectory(engine)

    else:
        console.print(f"[red]❌ Commande inconnue : {cmd}[/]")
        console.print("[dim]Tapez /help pour voir les commandes.[/]\n")

    return True


def display_spontaneous(assistant_msg: str, ai_emotion: dict):
    """Affiche un message spontané de l'IA."""
    console.print("\n")
    console.print(Rule(style="dim grey37"))

    spectra = ai_emotion.get("spectra", [])
    if spectra:
        console.print("  [dim]🤖 Spectres de l'IA :[/]")
        for s in spectra:
            console.print(f"     {render_spectrum_bar(s['name'], s['value'], s['icons'], trend=s.get('trend', '➡️'))}")

    # v4 : afficher le pattern de trajectoire
    pattern = ai_emotion.get("trajectory_pattern", {})
    if pattern and pattern.get("type") not in ("stable", "", None):
        ptype = pattern["type"]
        console.print(f"  [dim]📈 Trajectoire :[/] [bold]{ptype.upper()}[/]")

    console.print(Panel(
        Markdown(assistant_msg),
        title="[bold yellow]💭 Initiative de l'Assistant[/]",
        border_style="yellow",
        padding=(1, 2),
    ))
    console.print(Rule(style="dim grey37"))
    console.print("[bold bright_cyan]Vous > [/]", end="")


def run_cli(use_voice: bool = False, debug: bool = False):
    """Boucle principale du CLI avec support de messages spontanés."""

    # ── Logging ──────────────────────────────────────────────────────────
    log_level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    display_banner()

    if debug:
        console.print("[bold yellow]⚠️  Mode DEBUG activé — seuils spontanés réduits[/]\n")

    console.print("[dim]⏳ Initialisation du moteur IA...[/]")
    engine = ChatEngine(enable_sentiment=True, enable_rag=True)

    # ── Mode debug : réduire les seuils pour tester les spontanés ────────
    if debug and engine.emotion_engine:
        engine.emotion_engine.IDLE_THRESHOLD = 5       # 5s au lieu de 30s
        engine.emotion_engine.SPONTANEOUS_CHANCE = 0.95  # quasi-garanti
        console.print("[dim yellow]  → IDLE_THRESHOLD = 5s, SPONTANEOUS_CHANCE = 0.95[/]")

    voice_mgr = None
    if use_voice:
        console.print("[dim]🎙️  Initialisation du module vocal...[/]")
        from voice import VoiceManager
        try:
            voice_mgr = VoiceManager()
        except Exception as e:
            console.print(f"[red]Erreur d'initialisation vocale : {e}[/]")
            use_voice = False

    console.print("[green]✅ Moteur prêt ![/]\n")

    # ── Message de retrouvailles (si état chargé depuis une sauvegarde) ──
    em = engine.emotion_engine
    if em and em.total_sessions > 1:
        console.print(Panel(
            f"[bold]🐣 Âge :[/] {em.get_age_display()}  •  "
            f"[bold]Session :[/] #{em.total_sessions}  •  "
            f"[bold]Interactions :[/] {em.total_interactions}\n"
            f"[bold]Humeur actuelle :[/] {em.get_combined_display()}",
            title="[bold yellow]💾 État restauré[/]",
            border_style="yellow",
        ))
        console.print()

    # Flag pour éviter les conflits d'affichage
    is_processing = {"status": False}

    def check_spontaneous_loop():
        while True:
            time.sleep(10)
            if not is_processing["status"]:
                try:
                    result = engine.get_spontaneous_response()
                    if result:
                        msg, emotion = result
                        if msg and msg.strip():  # Ignorer les réponses vides
                            display_spontaneous(msg, emotion)
                        else:
                            logger.debug("Spontané: réponse vide ignorée côté CLI")
                except Exception as e:
                    logger.error("Erreur dans la boucle spontanée: %s", e, exc_info=True)

    # Lancer le thread de surveillance
    monitor_thread = threading.Thread(target=check_spontaneous_loop, daemon=True)
    monitor_thread.start()

    while True:
        try:
            if use_voice and voice_mgr:
                console.print("[dim italic]🎙️  Parlez (ou attendez le silence)...[/]")
                user_input = voice_mgr.listen()
                if user_input:
                    console.print(f"[bold bright_cyan]Vous (vocal) >[/] {user_input}")
                else:
                    continue
            else:
                user_input = console.input("[bold bright_cyan]Vous >[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            # Sauvegarder avant de quitter
            if engine.emotion_engine:
                engine.emotion_engine.save_state()
                console.print("\n[dim]💾 État émotionnel sauvegardé.[/]")
            console.print("[bright_cyan]👋 À bientôt ![/]\n")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if not handle_command(user_input, engine):
                break
            continue

        # Bloquer les messages spontanés pendant le traitement
        is_processing["status"] = True

        console.print()
        sentiment_result = None
        ai_emotion_result = None
        rag_sources = []
        response_parts = []

        try:
            with console.status("[dim]Réflexion...[/]", spinner="dots"):
                stream = engine.send_message_stream(user_input)
                first_chunk = True
                for token, sentiment, ai_emotion, sources in stream:
                    if first_chunk:
                        sentiment_result = sentiment
                        ai_emotion_result = ai_emotion
                        rag_sources = sources
                        display_emotions(sentiment_result, ai_emotion_result)
                        if sentiment_result:
                            console.print()
                        console.print("[bold bright_magenta]🤖 Assistant >[/] ", end="")
                        first_chunk = False
                    response_parts.append(token)

            full_response = "".join(response_parts)
            console.print()
            console.print(Panel(
                Markdown(full_response),
                border_style="bright_magenta",
                padding=(1, 2),
            ))

            display_sources(rag_sources)
            console.print()

            # Voix
            if use_voice and voice_mgr:
                voice_mgr.speak(full_response)
        finally:
            is_processing["status"] = False