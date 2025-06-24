let map = L.map('map').setView([55.751244, 37.618423], 12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
}).addTo(map);
fetch('/events').then(r=>r.json()).then(data=>{
    data.forEach(ev=>{
        L.marker([ev.lat, ev.lng]).addTo(map)
            .bindPopup(`<b>${ev.title}</b><br>${ev.description}`);
    });
});
