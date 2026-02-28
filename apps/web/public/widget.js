/**
 * PulseX-WDD Embeddable Widget Script
 * Add to any page: <script src="/widget.js" data-project="murano" defer></script>
 * 
 * The script creates a bottom-docked iframe pointing to /widget route.
 */
(function () {
    var script = document.currentScript || (function () {
        var scripts = document.getElementsByTagName('script');
        return scripts[scripts.length - 1];
    })();

    var project = script.getAttribute('data-project') || '';
    var region = script.getAttribute('data-region') || '';
    var lang = script.getAttribute('data-lang') || 'en';
    var baseUrl = script.src.replace('/widget.js', '');

    // Build iframe URL
    var params = new URLSearchParams();
    if (project) params.set('project', project);
    if (region) params.set('region', region);
    if (lang) params.set('lang', lang);
    var iframeSrc = baseUrl + '/widget' + (params.toString() ? '?' + params.toString() : '');

    // Container
    var container = document.createElement('div');
    container.id = 'pulsex-widget-container';
    Object.assign(container.style, {
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: '9999',
        width: '0',
        height: '0',
    });

    // Trigger button
    var btn = document.createElement('button');
    btn.id = 'pulsex-trigger-btn';
    btn.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    Object.assign(btn.style, {
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: '10000',
        width: '56px',
        height: '56px',
        borderRadius: '50%',
        background: '#CB2030',
        border: 'none',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '0 4px 20px rgba(0,0,0,0.18)',
        transition: 'transform 0.15s ease',
    });
    btn.addEventListener('mouseover', function () { btn.style.transform = 'scale(1.08)'; });
    btn.addEventListener('mouseout', function () { btn.style.transform = 'scale(1)'; });

    // Iframe
    var iframe = document.createElement('iframe');
    iframe.src = iframeSrc;
    iframe.id = 'pulsex-iframe';
    Object.assign(iframe.style, {
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: '9998',
        width: '390px',
        height: '600px',
        maxHeight: '90vh',
        border: 'none',
        borderRadius: '16px',
        boxShadow: '0 8px 40px rgba(0,0,0,0.15)',
        display: 'none',
        opacity: '0',
        transition: 'opacity 0.25s ease',
    });

    var open = false;
    function toggle() {
        open = !open;
        if (open) {
            iframe.style.display = 'block';
            setTimeout(function () { iframe.style.opacity = '1'; }, 10);
            btn.style.display = 'none';
        } else {
            iframe.style.opacity = '0';
            setTimeout(function () { iframe.style.display = 'none'; }, 260);
            btn.style.display = 'flex';
        }
    }

    btn.addEventListener('click', toggle);

    // Listen for close message from iframe
    window.addEventListener('message', function (e) {
        if (e.data === 'pulsex:close') { open = true; toggle(); }
    });

    document.body.appendChild(btn);
    document.body.appendChild(iframe);
})();
