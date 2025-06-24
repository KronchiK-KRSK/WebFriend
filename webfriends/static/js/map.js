let map = L.map('map').setView([55.751244, 37.618423], 12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
}).addTo(map);
let markers = [];
const mapIcons = {
    default: L.icon({iconUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',iconSize:[25,41],iconAnchor:[12,41]}),
    safe: L.icon({iconUrl:'https://cdn.jsdelivr.net/gh/pointhi/leaflet-color-markers@master/img/marker-icon-green.png',iconSize:[25,41],iconAnchor:[12,41]})
};
fetch('/events').then(r=>r.json()).then(data=>{
    data.forEach(item=>{
        const icon = item.safe ? mapIcons.safe : mapIcons.default;
        const marker = L.marker([item.lat, item.lng], {icon}).addTo(map);
        marker.bindPopup(`<b>${item.title}</b><br>${item.description || ''}`);
        marker.item = item;
        markers.push(marker);
    });
});

function applyFilters(){
    const term = document.getElementById('search').value.toLowerCase();
    const gender = document.getElementById('filterGender').value;
    const category = document.getElementById('filterCategory').value;
    const safeOnly = document.getElementById('filterSafe').checked;
    markers.forEach(m => {
        let visible = m.item.title.toLowerCase().includes(term);
        if(gender && m.item.type === 'user'){
            visible = visible && m.item.gender === gender;
        }
        if(category && m.item.type === 'event'){
            visible = visible && m.item.category === category;
        }
        if(safeOnly && m.item.type === 'event'){
            visible = visible && m.item.safe;
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
document.getElementById('filterCategory').addEventListener('change', applyFilters);
document.getElementById('filterSafe').addEventListener('change', applyFilters);
