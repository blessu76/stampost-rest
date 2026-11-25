"""Markup for the localized browser game."""

import json

from ipe_web_kit.seo import esc


def render_game(labels, artwork, stamps, max_queue, batch_points, name):
    def label(key):
        return esc(labels[key])

    def icon(stamp, size):
        return f'<img src="{artwork[stamp]}" width="{size}" height="{size}" alt="">'

    def parcel(size):
        return f"""<span class="game-parcel">
          <img class="game-parcel-paper" src="{artwork['envelope']}" width="{size}" height="{size}" alt="">
          <img class="game-parcel-stamp" width="24" height="24" alt="" hidden>
          <span class="game-parcel-gold" aria-hidden="true">✦</span>
          <span class="game-sr" data-parcel-label></span>
        </span>"""

    best_stars = '<span class="game-stars" data-part="bestStars"></span>'
    hud = "".join(f"""<div class="game-stat">
      <span id="game-{key}-label">{label(title)}</span>
      <div><strong data-part="{key}"></strong>{best_stars if key == "best" else ""}</div>
      <progress data-part="{key}Meter" aria-labelledby="game-{key}-label" max="1" value="0"></progress>
    </div>""" for key, title in (("time", "timeLeft"), ("score", "score"), ("best", "best")))
    preview = "".join(f"<li>{parcel(24)}</li>" for _ in range(3))
    queue = "".join(f"""<li>
        {parcel(50)}
        <span class="game-ruler" aria-hidden="true">+{batch_points(i)}</span>
      </li>""" for i in range(1, max_queue + 1))
    buttons = "".join(f"""<button class="stamp game-stamp" type="button" data-stamp="{stamp}" disabled>
      {icon(stamp, 24)}<span>{label(stamp_key)}</span><b data-count aria-hidden="true">0</b>
    </button>""" for stamp, stamp_key in zip(stamps, ("stampFlower", "stampMoon", "stampStar")))
    combo_slots = '<i></i>' * 10
    language_data = json.dumps(labels, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<section class="game wrap" data-stampost-game aria-labelledby="game-title">
  <h1 class="game-sr" id="game-title">{esc(name)}</h1>
  <div class="game-hud">{hud}</div>
  <div class="game-combo">
    <div class="game-combo-slots" data-part="comboSlots" aria-hidden="true">{combo_slots}</div>
    <strong data-part="combo"></strong>
    <span class="game-combo-time" data-part="comboTime" hidden aria-hidden="true"></span>
  </div>
  <div class="game-stage" role="group" aria-label="{label('sceneLabel')}">
    <img class="game-mailbox" src="{artwork['mailbox']}" width="137" height="123" alt="">
    <div class="game-intake">
      <small data-part="intakeLabel">{label('intakeNow')}</small>
      <strong data-part="intakeTitle"></strong>
      <span data-part="intakeDetail"></span>
      <span class="game-new-best" data-part="newBest" hidden>{label('newBest')}</span>
    </div>
    <div class="game-next" data-part="next">
      <b id="game-next-label">{label('upcomingLabel')}</b>
      <ol aria-labelledby="game-next-label">{preview}</ol>
    </div>
  </div>
  <div class="game-desk" role="group" aria-label="{label('workbenchLabel')}">
    <div class="game-queue-head">
      <strong>{label('queue')}</strong>
      <div class="game-queue-counts" data-part="queueCounts" aria-hidden="true">
        {"".join(f'<span>{icon(stamp, 12)}<b>0</b></span>' for stamp in stamps)}
      </div>
      <span class="game-capacity" data-part="capacity"></span>
    </div>
    <div class="game-belt" data-part="belt">
      <progress class="game-arrival" data-part="arrival" max="1" value="0" aria-label="{label('upcomingLabel')}"></progress>
      <ol class="game-queue" data-part="queue" aria-label="{label('beltLabel')}">{queue}</ol>
      <span class="game-rail" aria-hidden="true"></span>
      <div class="game-imprint" data-part="imprint" aria-hidden="true"></div>
      <output class="game-popup" data-part="popup" aria-hidden="true" aria-live="off" hidden></output>
    </div>
    <div class="game-rating" data-part="rating" hidden>
      <span class="game-stars" data-part="resultStars"></span>
      <span data-part="nextStar"></span>
      <span data-part="bestCombo"></span>
    </div>
    <p class="game-instructions" data-part="instructions">{label('instructions')}</p>
    <div class="game-stamps" role="group" aria-label="{label('stampRowLabel')}">{buttons}</div>
    <div class="game-actions">
      <button type="button" class="action game-start" data-part="start" disabled>{label('start')}</button>
      <p class="game-marker" data-part="marker" hidden></p>
      <button type="button" class="game-pause" data-part="pause" hidden>{label('pause')}</button>
    </div>
    <div class="game-totals">
      <span><i aria-hidden="true">✉</i><b data-part="delivered"></b></span>
      <span><i aria-hidden="true">▤</i><b data-part="longest"></b></span>
      <a href="#rules">{label('help')}</a>
    </div>
  </div>
  <div class="game-sr" data-part="announcement" role="status"></div>
  <script type="application/json" data-play-copy>{language_data}</script>
</section>"""
