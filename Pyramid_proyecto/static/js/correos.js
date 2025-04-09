document.getElementById("btnTraerCorreos").addEventListener("click", async function() {
    let response = await fetch("/traer_correos");
    let correos = await response.json();
    let lista = document.getElementById("listaCorreos");
    lista.innerHTML = "";
    correos.forEach(correo => {
        let li = document.createElement("li");
        li.textContent = `${correo.remitente}: ${correo.asunto}`;
        lista.appendChild(li);
    });
});

document.getElementById("formCorreo").addEventListener("submit", async function(event) {
    event.preventDefault();
    let data = {
        destinatario: document.getElementById("destinatario").value,
        asunto: document.getElementById("asunto").value,
        mensaje: document.getElementById("mensaje").value
    };
    let response = await fetch("/enviar_correo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
    let result = await response.json();
    alert(result.message);
});
