/* 70Scholar — progressive-enhancement front end.
   The whole site is server-rendered; this file only adds the two AJAX uploads
   plus small quality-of-life behaviours. Every block is guarded so a missing
   element on any page is harmless. */
(function () {
  'use strict';

  document.documentElement.classList.add('has-js');

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function readAsDataURL(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(String(reader.result)); };
      reader.onerror = function () { reject(new Error('Could not read the file.')); };
      reader.readAsDataURL(file);
    });
  }

  function postJSON(url, csrf, payload) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrf
      },
      body: JSON.stringify(payload),
      credentials: 'same-origin'
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok || !data.ok) {
          throw new Error(data.error || ('Upload failed (HTTP ' + res.status + ').'));
        }
        return data;
      });
    });
  }

  function setStatus(el, message, kind) {
    if (!el) return;
    el.textContent = message;
    el.classList.remove('is-error', 'is-success');
    if (kind) el.classList.add('is-' + kind);
    el.setAttribute('aria-live', 'polite');
  }

  function withBusyButton(button, task) {
    if (!button) return task();
    var original = button.textContent;
    button.disabled = true;
    button.textContent = 'Uploading…';
    return task().then(function (result) {
      button.disabled = false;
      button.textContent = original;
      return result;
    }, function (err) {
      button.disabled = false;
      button.textContent = original;
      throw err;
    });
  }

  /* ---------------------------------------------------- profile photo upload */
  var photoInput = $('#profilePhoto');
  var photoButton = $('#uploadProfilePhoto');
  var photoStatus = $('#profileUploadStatus');
  var photoBox = $('.upload-box.profile-upload');

  if (photoInput && photoButton && photoBox) {
    photoButton.addEventListener('click', function () {
      var file = photoInput.files && photoInput.files[0];
      if (!file) { setStatus(photoStatus, 'Choose an image first.', 'error'); return; }
      if (!/^image\//.test(file.type)) { setStatus(photoStatus, 'Please choose an image file.', 'error'); return; }
      if (file.size > 10 * 1024 * 1024) { setStatus(photoStatus, 'That image is larger than 10 MB.', 'error'); return; }

      var csrf = photoBox.getAttribute('data-account-csrf') || '';
      setStatus(photoStatus, 'Uploading your photo…');

      withBusyButton(photoButton, function () {
        return readAsDataURL(file).then(function (dataUrl) {
          return postJSON('/api/profile-photo', csrf, {
            filename: file.name,
            mime: file.type || 'image/jpeg',
            data: dataUrl
          });
        });
      }).then(function (result) {
        var url = result.url + '?v=' + Date.now();
        var avatar = $('#profileAvatar');
        if (avatar) {
          avatar.textContent = '';
          var img = document.createElement('img');
          img.src = url;
          img.alt = 'Your profile photo';
          avatar.appendChild(img);
        }
        $$('.nav-profile').forEach(function (link) {
          link.textContent = '';
          var navImg = document.createElement('img');
          navImg.src = url;
          navImg.alt = 'Profile photo';
          link.appendChild(navImg);
        });
        setStatus(photoStatus, 'Profile photo updated.', 'success');
        photoInput.value = '';
      }).catch(function (err) {
        setStatus(photoStatus, err.message, 'error');
      });
    });
  }

  /* ---------------------------------------------------- project asset upload */
  var assetInput = $('#assetFile');
  var assetButton = $('#uploadAsset');
  var assetStatus = $('#uploadStatus');
  var assetBox = $('.upload-box[data-project-id][data-csrf]');

  if (assetInput && assetButton && assetBox) {
    assetButton.addEventListener('click', function () {
      var file = assetInput.files && assetInput.files[0];
      if (!file) { setStatus(assetStatus, 'Choose a file first.', 'error'); return; }

      var csrf = assetBox.getAttribute('data-csrf') || '';
      var projectId = assetBox.getAttribute('data-project-id') || '';
      var prettySize = file.size >= 1024 * 1024
        ? (file.size / 1024 / 1024).toFixed(1) + ' MB'
        : Math.max(1, Math.round(file.size / 1024)) + ' KB';
      setStatus(assetStatus, 'Uploading ' + file.name + ' (' + prettySize + ')…');

      withBusyButton(assetButton, function () {
        return readAsDataURL(file).then(function (dataUrl) {
          return postJSON('/api/upload', csrf, {
            project_id: Number(projectId),
            filename: file.name,
            mime: file.type || 'application/octet-stream',
            data: dataUrl
          });
        });
      }).then(function (result) {
        var list = $('.asset-list', assetBox);
        if (list) {
          var placeholder = $$('li', list).filter(function (li) {
            return /No uploaded files yet/i.test(li.textContent);
          });
          placeholder.forEach(function (li) { li.remove(); });

          var li = document.createElement('li');
          var link = document.createElement('a');
          link.href = result.download_url;
          link.textContent = result.filename || file.name;
          link.setAttribute('download', '');
          li.appendChild(link);
          list.insertBefore(li, list.firstChild);
        }
        setStatus(assetStatus, 'Uploaded ' + (result.filename || file.name) + '.', 'success');
        assetInput.value = '';
      }).catch(function (err) {
        setStatus(assetStatus, err.message, 'error');
      });
    });
  }

  /* ---------------------------------------------------- filter bar convenience */
  $$('.filter-bar select').forEach(function (select) {
    select.addEventListener('change', function () {
      var form = select.closest('form');
      if (form && !form.querySelector('[type="submit"]')) form.submit();
    });
  });

  /* ---------------------------------------------------- confirm destructive admin actions */
  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form || !form.matches('form[action^="/admin/"]')) return;
    var trigger = event.submitter || form.querySelector(':focus');
    var value = (trigger && (trigger.value || trigger.getAttribute('value'))) || '';
    if (/^delete$/i.test(value) && !window.confirm('Are you sure? This cannot be undone.')) {
      event.preventDefault();
    }
  });

  /* ---------------------------------------------------- prevent accidental double submits
     NOTE: never disable the buttons here. Many server handlers read the clicked
     button's name/value (admin actions, pledge options); a disabled button is
     omitted from the submitted form data. Only block the second submit event. */
  $$('form[method="post"]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (form.dataset.submitting === '1') { event.preventDefault(); return; }
      form.dataset.submitting = '1';
      // Safety net: clear the guard if navigation never happens.
      window.setTimeout(function () { form.dataset.submitting = '0'; }, 8000);
    });
  });

  /* ---------------------------------------------------- reveal on scroll */
  var revealTargets = $$('.journey-step, .opp-card, .market-card, .listing-card, .stat-card, .mini-card');
  if ('IntersectionObserver' in window && revealTargets.length) {
    revealTargets.forEach(function (el) { el.classList.add('reveal-on-scroll'); });
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
    revealTargets.forEach(function (el) { observer.observe(el); });
  }

  /* ---------------------------------------------------- typewriter: write + erase */
  var tw = $('#typewriter');
  if (tw && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var words = (document.documentElement.getAttribute('data-words') || '').split('|').filter(Boolean);
    if (!words.length) {
      words = ['Scholarships','Internships','Competitions','Pre-university courses',
               'University exam prep','Grants','Project funding','Student applications',
               'Mentorship','Marketplace','Research opportunities','A future you can build'];
    }
    var wi = 0, ci = 0, erasing = false;
    function tick() {
      var word = words[wi];
      tw.textContent = erasing ? word.slice(0, ci--) : word.slice(0, ci++);
      var delay = erasing ? 42 : 85;
      if (!erasing && ci > word.length) { erasing = true; delay = 1500; }
      else if (erasing && ci < 0) { erasing = false; wi = (wi + 1) % words.length; ci = 0; delay = 320; }
      window.setTimeout(tick, delay);
    }
    tick();
  } else if (tw) { tw.textContent = 'Scholarships, courses, exam prep and funding.'; }

  /* ---------------------------------------------------- auto-advancing photo slideshow */
  var show = $('#slideshow');
  if (show) {
    var slides = $$('.slide', show), dots = $$('.slide-dot', show), counter = $('#slideCurrent');
    var idx = 0, timer = null, INTERVAL = 5000;
    function go(n) {
      idx = (n + slides.length) % slides.length;
      slides.forEach(function (el, i) { el.classList.toggle('is-active', i === idx); });
      dots.forEach(function (el, i) { el.classList.toggle('is-active', i === idx); });
      if (counter) counter.textContent = String(idx + 1);
    }
    function play() { stop(); timer = window.setInterval(function () { go(idx + 1); }, INTERVAL); }
    function stop() { if (timer) { window.clearInterval(timer); timer = null; } }
    $$('.slide-nav', show).forEach(function (b) {
      b.addEventListener('click', function () { go(idx + Number(b.getAttribute('data-dir'))); play(); });
    });
    dots.forEach(function (d) {
      d.addEventListener('click', function () { go(Number(d.getAttribute('data-go'))); play(); });
    });
    show.addEventListener('mouseenter', stop);
    show.addEventListener('mouseleave', play);
    document.addEventListener('visibilitychange', function () { document.hidden ? stop() : play(); });
    go(0); play();
  }

  /* ---------------------------------------------------- cursor-following auto description */
  var tip = document.createElement('div');
  tip.id = 'hoverTooltip'; tip.setAttribute('role', 'tooltip'); document.body.appendChild(tip);
  function moveTip(ev) {
    var pad = 16, w = tip.offsetWidth, h = tip.offsetHeight;
    var x = ev.clientX + pad, y = ev.clientY + pad;
    if (x + w > window.innerWidth - 8) x = ev.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = ev.clientY - h - pad;
    tip.style.left = Math.max(8, x) + 'px';
    tip.style.top = Math.max(8, y) + 'px';
  }
  document.addEventListener('mouseover', function (ev) {
    var el = ev.target.closest ? ev.target.closest('[data-tooltip]') : null;
    if (!el) return;
    tip.textContent = el.getAttribute('data-tooltip') || '';
    tip.classList.add('is-visible'); moveTip(ev);
  });
  document.addEventListener('mousemove', function (ev) { if (tip.classList.contains('is-visible')) moveTip(ev); });
  document.addEventListener('mouseout', function (ev) {
    var el = ev.target.closest ? ev.target.closest('[data-tooltip]') : null;
    if (el && (!ev.relatedTarget || !el.contains(ev.relatedTarget))) tip.classList.remove('is-visible');
  });

  /* ---------------------------------------------------- animated counters */
  var counters = $$('[data-count]');
  if ('IntersectionObserver' in window && counters.length) {
    var co = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target, target = Number(el.getAttribute('data-count')) || 0, start = null;
        function step(ts) {
          if (!start) start = ts;
          var p = Math.min(1, (ts - start) / 1200);
          el.textContent = String(Math.round(target * (1 - Math.pow(1 - p, 3))));
          if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step); co.unobserve(el);
      });
    }, { threshold: .4 });
    counters.forEach(function (c) { co.observe(c); });
  }

  /* ---------------------------------------------------- sticky-header anchor offset */
  $$('section[id], div[id]').forEach(function (el) {
    el.style.scrollMarginTop = '86px';
  });
})();
