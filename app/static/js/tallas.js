document.addEventListener("change", function (e) {
    if (!e.target.classList.contains("marca-select")) return;

    const marcaSelect = e.target;
    const fila = marcaSelect.closest("tr");
    const tallaSelect = fila.querySelector(".talla-select");

    const idMarca = marcaSelect.value;

    // Limpiar tallas
    tallaSelect.innerHTML = '<option value="">-- Selecciona Talla --</option>';

    if (!idMarca) return;

    fetch(`/tallas/${idMarca}`)
        .then(res => res.json())
        .then(data => {
            data.forEach(talla => {
                const option = document.createElement("option");
                option.value = talla;
                option.textContent = talla;
                tallaSelect.appendChild(option);
            });
        })
        .catch(err => console.error("Error cargando tallas:", err));
});
