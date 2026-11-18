"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const campaignId = document.body.dataset.campaignId;
const pendingKey = "keitaro-wrapper-pending";
let csrf = "";
let currentCampaign = null;
let submitting = false;
const statusNames = {
  running: "Выполняется",
  succeeded: "Подтверждено",
  failed: "Ошибка",
  conflict: "Конфликт",
  partial: "Создано частично",
  unknown: "Нужна сверка",
  manual_review: "Нужна ручная проверка",
};
const offerStates = {
  active: "Активен",
  new: "Добавлен в черновик",
  restored: "Возвращён в черновик",
  removed: "Будет удалён",
  archived: "Removed · архив",
  disabled: "Отключён в Keitaro",
};

function notice(message, error = false) {
  const box = $("#notice");
  box.textContent = message;
  box.className = error ? "notice error" : "notice";
  box.hidden = !message;
}

async function read(path) {
  const response = await fetch(`/api/v1${path}`, {
    credentials: "same-origin",
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error?.message || "Не удалось получить данные.");
  return data;
}

function pendingRecord() {
  try {
    return JSON.parse(sessionStorage.getItem(pendingKey) || "null");
  } catch {
    return null;
  }
}

function showPending() {
  const box = $("#pending");
  const pending = pendingRecord();
  box.hidden = !pending;
  if (pending)
    box.innerHTML = `<p>Ответ на предыдущую команду не получен. Проверьте её статус перед новым действием.</p><button type="button" data-pending="check">Проверить статус</button><button type="button" data-pending="retry">Повторить тот же запрос</button>`;
}

async function send(path, body, method = "POST", existing = null) {
  if (submitting) return null;
  if (pendingRecord() && !existing) {
    showPending();
    notice("Сначала проверьте предыдущую команду.", true);
    return null;
  }
  const command = existing || { key: crypto.randomUUID(), path, body, method };
  sessionStorage.setItem(pendingKey, JSON.stringify(command));
  submitting = true;
  document.body.setAttribute("aria-busy", "true");
  notice("Выполняем команду…");
  try {
    let response;
    let data;
    try {
      response = await fetch(`/api/v1${command.path}`, {
        method: command.method,
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
          "Idempotency-Key": command.key,
        },
        body: JSON.stringify(command.body),
      });
      data = await response.json();
      const hasReceipt = data?.id && data?.status && data?.campaign_id;
      const rejectedBeforeStart =
        data?.error?.details?.command_state === "not_started";
      // A server failure without a receipt does not prove that no write occurred.
      // Rejection of a retry also says nothing about the original request.
      if (
        !hasReceipt &&
        (response.ok ||
          (response.status >= 500 && !rejectedBeforeStart) ||
          existing)
      ) {
        throw new Error("Command outcome is unknown");
      }
    } catch {
      showPending();
      notice(
        "Результат команды не подтверждён; её ключ сохранён в этой вкладке. Проверьте статус или повторите тот же запрос.",
        true,
      );
      return null;
    }

    sessionStorage.removeItem(pendingKey);
    showPending();
    if (!response.ok) {
      notice(data.error?.message || "Не удалось выполнить команду.", true);
    } else {
      notice(
        data.status === "succeeded"
          ? "Изменения сохранены."
          : `${statusNames[data.status] || data.status}. Состояние доступно в разделе операций.`,
      );
    }
    // A failed screen refresh must not erase an already confirmed command result.
    try {
      await refresh(false);
    } catch {
      notice(
        "Ответ на команду получен, но экран не обновился. Нажмите «Обновить экран».",
        true,
      );
    }
    return data.campaign_id ? data : null;
  } finally {
    submitting = false;
    document.body.removeAttribute("aria-busy");
  }
}

function pickerHTML(id) {
  return `
    <div class="offer-picker">
      <label for="query-${id}">Добавить оффер</label>
      <input id="query-${id}" class="offer-query" type="search"
        placeholder="Название или ID" autocomplete="off">
      <select name="offer_id" aria-label="Оффер для добавления" required>
        <option value="">Начните поиск</option>
      </select>
      <small class="search-status" aria-live="polite"></small>
    </div>`;
}

function pinEditorHTML(stream, offer) {
  if (!offer.active) return "";
  const disabled = stream.can_edit ? "" : "disabled";
  const unpinButton = offer.pinned
    ? `<button type="submit" name="pin" value="false" ${disabled}>Снять</button>`
    : "";
  return `
    <form class="pin-editor" data-edit="pin" data-stream="${stream.id}" data-offer="${offer.offer_id}">
      <input name="weight" type="number" min="1" max="100" step="1" value="${offer.weight || 1}"
        aria-label="Закреплённый вес оффера ${offer.offer_id}" ${disabled}>
      <button type="submit" name="pin" value="true" ${disabled}>${offer.pinned ? "Изменить" : "Закрепить"}</button>
      ${unpinButton}
    </form>`;
}

function offerRowHTML(stream, offer) {
  const disabled = stream.can_edit ? "" : "disabled";
  const action = offer.active ? "remove" : "restore";
  const actionLabel = offer.active ? "Remove" : "Bring Back";
  const weight = Math.max(0, Math.min(100, offer.weight));
  return `
    <tr class="${offer.active ? "" : "inactive"}">
      <td>
        <span class="offer-name">${escapeHTML(offer.name)}</span>
        <span class="offer-id">#${offer.offer_id}</span>
        <span class="offer-state">${offerStates[offer.status]}</span>
      </td>
      <td>
        <span class="weight">${offer.weight}%</span>
        <progress class="allocation" max="100" value="${weight}"
          aria-label="Доля оффера ${offer.offer_id}"></progress>
        ${pinEditorHTML(stream, offer)}
      </td>
      <td>
        <button type="button" data-action="${action}" data-stream="${stream.id}"
          data-offer="${offer.offer_id}" ${disabled}>${actionLabel}</button>
      </td>
    </tr>`;
}

function streamFooterHTML(stream) {
  if (stream.read_only_reason || !stream.available) return "";
  return `
    <div class="stream-foot">
      <form data-edit="add" data-stream="${stream.id}">
        <div class="add-fields">
          ${pickerHTML(stream.id)}
          <button type="submit" class="secondary" ${stream.can_edit ? "" : "disabled"}>Добавить</button>
        </div>
      </form>
      <div class="total">Активные доли <strong>${stream.total}%</strong></div>
    </div>`;
}

function streamHTML(stream) {
  const rows = stream.offers
    .map((offer) => offerRowHTML(stream, offer))
    .join("");
  let status = stream.available ? "Синхронизирован" : "Недоступен";
  if (stream.dirty) status = "Есть изменения";
  const description = stream.read_only_reason
    ? `<p class="stream-description">${escapeHTML(stream.read_only_reason)}</p>`
    : "";
  const content = rows
    ? `<table class="offer-table">
        <thead><tr><th scope="col">Оффер</th><th scope="col">Доля трафика</th><th scope="col">Действие</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`
    : `<p class="stream-description">В этом потоке нет офферов для редактирования.</p>`;
  return `
    <section class="stream ${stream.dirty ? "dirty" : ""}" aria-labelledby="stream-${stream.id}">
      <div class="stream-head">
        <div class="stream-title">
          <h2 id="stream-${stream.id}">${escapeHTML(stream.name)}</h2>
          <span class="stream-id">#${stream.id}</span>
          <span class="status ${stream.dirty ? "changed" : ""}">${status}</span>
        </div>
        <div class="stream-actions">
          <button type="button" data-action="cancel" data-stream="${stream.id}"
            ${stream.can_cancel ? "" : "disabled"}>Cancel</button>
          <button type="button" class="primary" data-action="push" data-stream="${stream.id}"
            ${stream.can_push ? "" : "disabled"}>Push to KT</button>
        </div>
      </div>
      ${description}
      ${content}
      ${streamFooterHTML(stream)}
    </section>`;
}

function resolutionFormHTML(operation) {
  if (!operation.can_resolve) return "";
  return `
    <details>
      <summary>Ручная проверка результата</summary>
      <form class="resolution-form" data-edit="resolve" data-operation="${operation.id}">
        <p>Сначала убедитесь в Keitaro, что предыдущий запрос завершён. Принятие текущего состояния сбросит черновик этого потока.</p>
        <label>Решение
          <select name="decision" required>
            <option value="adopt_current">Принять текущее состояние</option>
            <option value="not_applied">Подтверждено: запись не выполнена</option>
          </select>
        </label>
        <label>Что проверено<textarea name="note" required maxlength="1000" rows="2"></textarea></label>
        <label class="check">
          <input type="checkbox" name="confirmation" required>Подтверждаю: незавершённых запросов в Keitaro нет
        </label>
        <button type="submit" class="danger">Зафиксировать решение</button>
      </form>
    </details>`;
}

function operationHTML(operation) {
  const title =
    {
      create: "Создание кампании",
      push: "Публикация потока",
      fetch: "Получение потоков",
      import: "Импорт кампании",
    }[operation.kind] || "Операция";
  const reconcile = operation.can_reconcile
    ? `<button type="button" data-control="reconcile" data-operation="${operation.id}">Проверить в Keitaro</button>`
    : "";
  const resume = operation.can_resume
    ? `<button type="button" data-control="resume" data-operation="${operation.id}">Продолжить операцию</button>`
    : "";
  return `
    <article class="operation">
      <div class="operation-header">
        <strong>${title}${operation.stream_id ? ` #${operation.stream_id}` : ""}</strong>
        <span class="status ${operation.status === "succeeded" ? "" : "changed"}">
          ${statusNames[operation.status] || escapeHTML(operation.status)}
        </span>
      </div>
      <p>${escapeHTML(operation.error?.message || "")}</p>
      <small>ID ${escapeHTML(operation.id)}${operation.stage ? ` · этап ${escapeHTML(operation.stage)}` : ""}</small>
      ${reconcile}
      ${resume}
      ${resolutionFormHTML(operation)}
    </article>`;
}

async function refresh(clearNotice = true) {
  if (clearNotice) notice("");
  if (!campaignId) {
    const data = await read("/campaigns");
    $("#campaign-list").innerHTML = data.items.length
      ? data.items
          .map(
            (c) =>
              `<a class="campaign-row" href="/campaigns/${encodeURIComponent(c.id)}"><div><strong>${escapeHTML(c.name)}</strong><span>${c.keitaro_id ? `Keitaro #${c.keitaro_id}` : "Создаётся"} · ${escapeHTML({ active: "Активна", disabled: "Выключена", creating: "Создаётся", importing: "Импортируется" }[c.state] || c.state)}</span></div><span class="row-end">Открыть</span></a>`,
          )
          .join("")
      : `<div class="empty"><strong>Рабочий список пока пуст</strong><p>Введите ID существующей кампании или создайте новую.</p></div>`;
    return;
  }
  currentCampaign = await read(`/campaigns/${campaignId}`);
  $("#campaign-title").textContent = currentCampaign.name;
  document.title = `${currentCampaign.name} · Keitaro Wrapper`;
  $("#campaign-meta").textContent =
    `Keitaro #${currentCampaign.keitaro_id || "—"} · ${currentCampaign.last_fetched_at ? `Получено ${new Date(currentCampaign.last_fetched_at).toLocaleString("ru-RU")}` : "Ещё не синхронизирована"}${currentCampaign.busy ? " · Есть незавершённая операция" : ""}`;
  $("#fetch").disabled = !currentCampaign.can_fetch;
  $("#fetch").setAttribute("aria-describedby", "fetch-note");
  const fetchNote = $("#fetch-note");
  fetchNote.hidden = currentCampaign.can_fetch;
  fetchNote.textContent = currentCampaign.busy
    ? "Fetch недоступен: сначала завершите или проверьте незавершённую операцию в журнале ниже."
    : currentCampaign.streams.some((stream) => stream.dirty)
      ? "Для Fetch сначала выполните Push to KT или Cancel для каждого изменённого потока."
      : "Fetch станет доступен после подтверждения создания или импорта кампании.";
  const link = $("#campaign-link");
  link.hidden = true;
  link.removeAttribute("href");
  if (currentCampaign.url) {
    try {
      const url = new URL(currentCampaign.url);
      if (["http:", "https:"].includes(url.protocol)) {
        link.href = url.href;
        link.hidden = false;
      }
    } catch {
      /* An invalid tracking URL must never become a clickable link. */
    }
  }
  $("#streams").innerHTML = currentCampaign.streams.length
    ? currentCampaign.streams.map(streamHTML).join("")
    : `<div class="empty"><strong>Потоки ещё не получены</strong><p>Проверьте состояние операции ниже.</p></div>`;
  $("#operation-list").innerHTML =
    currentCampaign.operations.map(operationHTML).join("") ||
    `<p class="muted">Пока нет операций.</p>`;
}

document.addEventListener("input", (event) => {
  const input = event.target;
  if (!input.matches(".offer-query")) return;
  const picker = input.closest(".offer-picker");
  const select = $("select", picker);
  const status = $(".search-status", picker);
  clearTimeout(input.searchTimer);
  select.innerHTML = '<option value="">Выберите оффер</option>';
  status.textContent = input.value.trim() ? "Поиск…" : "";
  const query = input.value.trim();
  if (!query) return;
  input.searchTimer = setTimeout(async () => {
    try {
      const data = await read(`/offers?q=${encodeURIComponent(query)}`);
      if (input.value.trim() !== query || !input.isConnected) return;
      select.innerHTML += data.items
        .map(
          (o) =>
            `<option value="${o.id}">#${o.id} · ${escapeHTML(o.name)}</option>`,
        )
        .join("");
      status.textContent = data.total
        ? `Найдено: ${data.total}`
        : "Офферы не найдены";
    } catch (error) {
      status.textContent = error.message;
    }
  }, 300);
});

document.addEventListener("submit", async (event) => {
  const form = event.target;
  event.preventDefault();
  const data = new FormData(form);
  try {
    if (form.id === "import-form" || form.id === "create-form") {
      const importing = form.id === "import-form";
      const payload = importing
        ? { keitaro_campaign_id: Number(data.get("keitaro_campaign_id")) }
        : {
            name: data.get("name"),
            country_code: data.get("country_code"),
            offer_id: Number(data.get("offer_id")),
          };
      const result = await send(
        importing ? "/campaigns/import" : "/campaigns",
        payload,
      );
      if (result?.campaign_id)
        location.assign(`/campaigns/${encodeURIComponent(result.campaign_id)}`);
      return;
    }
    if (form.dataset.edit === "resolve") {
      const operation = currentCampaign.operations.find(
        (o) => o.id === form.dataset.operation,
      );
      await send(`/operations/${operation.id}/resolve`, {
        expected_operation_revision: operation.revision,
        decision: data.get("decision"),
        confirmation: data.has("confirmation"),
        note: data.get("note"),
      });
      return;
    }
    const stream = currentCampaign.streams.find(
      (s) => s.id === Number(form.dataset.stream),
    );
    if (form.dataset.edit === "add")
      await send(`/streams/${stream.id}/offers`, {
        expected_revision: stream.revision,
        offer_id: Number(data.get("offer_id")),
      });
    if (form.dataset.edit === "pin") {
      const pinned = event.submitter?.value !== "false";
      await send(
        `/streams/${stream.id}/offers/${form.dataset.offer}/pin`,
        {
          expected_revision: stream.revision,
          pinned,
          weight: pinned ? Number(data.get("weight")) : null,
        },
        "PUT",
      );
    }
  } catch (error) {
    notice(error.message, true);
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button || button.disabled || submitting) return;
  try {
    if (button.id === "reload" || button.id === "refresh-local")
      await refresh();
    if (button.id === "fetch")
      await send(`/campaigns/${campaignId}/fetch`, {
        expected_revision: currentCampaign.revision,
      });
    if (button.dataset.action) {
      const stream = currentCampaign.streams.find(
        (s) => s.id === Number(button.dataset.stream),
      );
      const path = button.dataset.offer
        ? `/streams/${stream.id}/offers/${button.dataset.offer}/${button.dataset.action}`
        : `/streams/${stream.id}/${button.dataset.action}`;
      await send(path, { expected_revision: stream.revision });
    }
    if (button.dataset.control) {
      const operation = currentCampaign.operations.find(
        (o) => o.id === button.dataset.operation,
      );
      await send(`/operations/${operation.id}/${button.dataset.control}`, {
        expected_operation_revision: operation.revision,
      });
    }
    if (button.dataset.pending) {
      const pending = pendingRecord();
      if (!pending) return;
      if (button.dataset.pending === "retry") {
        const result = await send(
          pending.path,
          pending.body,
          pending.method,
          pending,
        );
        if (result?.campaign_id && result.campaign_id !== campaignId) {
          location.assign(
            `/campaigns/${encodeURIComponent(result.campaign_id)}`,
          );
        }
      } else {
        let operation = await read(`/operations/${pending.key}`);
        if (operation.parent_operation_id) {
          operation = await read(
            `/operations/${operation.parent_operation_id}`,
          );
        }
        sessionStorage.removeItem(pendingKey);
        showPending();
        if (operation.campaign_id && operation.campaign_id !== campaignId)
          location.assign(`/campaigns/${operation.campaign_id}`);
        else {
          await refresh();
          notice(
            `Статус: ${statusNames[operation.status] || operation.status}`,
          );
        }
      }
    }
  } catch (error) {
    notice(error.message, true);
  }
});

async function boot() {
  showPending();
  try {
    const settings = await read("/bootstrap");
    csrf = settings.csrf_token;
    $("#connection").textContent = settings.integration_configured
      ? "API настроен · статус проверяется при запросе"
      : "API-ключ не настроен";
    if (!campaignId) {
      $("#prefix-note").textContent = `Префикс: ${settings.prefix}`;
      $("#country").innerHTML += settings.countries
        .map(
          (c) =>
            `<option value="${escapeHTML(c.code)}">${escapeHTML(c.name)} · ${c.code}</option>`,
        )
        .join("");
      if (!settings.creation_configured || !settings.integration_configured) {
        $("#create-form button[type=submit]").disabled = true;
        $("#create-note").textContent =
          "Для создания нужны API-ключ и проверенный профиль маршрутизации. Сохранённые кампании доступны в списке.";
      }
    }
    await refresh(false);
  } catch (error) {
    notice(error.message, true);
  }
}
boot();
