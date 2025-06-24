let map = L.map('map').setView([55.751244, 37.618423], 12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
}).addTo(map);
let markers = [];
fetch('/events').then(r=>r.json()).then(data=>{
    data.forEach(item=>{
        const marker = L.marker([item.lat, item.lng]).addTo(map);
        marker.bindPopup(`<b>${item.title}</b><br>${item.description || ''}`);
        marker.item = item;
        markers.push(marker);
    });
});

function applyFilters(){
    const term = document.getElementById('search').value.toLowerCase();
    const gender = document.getElementById('filterGender').value;
    markers.forEach(m => {
        let visible = m.item.title.toLowerCase().includes(term);
        if(gender && m.item.type === 'user'){
            visible = visible && m.item.gender === gender;
        }
        if(visible){
            m.addTo(map);
        }else{
            map.removeLayer(m);
        }
    });
}

document.getElementById('search').addEventListener('input', applyFilters);
document.getElementById('filterGender').addEventListener('change', applyFilters);
