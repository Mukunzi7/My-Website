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

  /* ---------------------------------------------------- sticky-header anchor offset */
  $$('section[id], div[id]').forEach(function (el) {
    el.style.scrollMarginTop = '86px';
  });
})();
