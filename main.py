import matplotlib
matplotlib.use("Agg")
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt
import io, base64

app = FastAPI(title="Quantum Chat API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SendReq(BaseModel):
    bits: str  # "00","01","10","11"
    shots: int = 1024

def circuit_png(qc):
    """Return a base64 PNG of the circuit drawing."""
    fig = qc.draw(output="mpl", fold=-1)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def histogram_png(counts):
    """Return a base64 PNG of the measurement histogram."""
    fig = plot_histogram(counts)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def superdense(bits: str, shots: int = 1024):
    if bits not in {"00", "01", "10", "11"}:
        raise ValueError("bits must be one of '00','01','10','11'")

    qc = QuantumCircuit(2, 2)  # q0=Alice, q1=Bob

    # 1) Share entanglement
    qc.h(0)
    qc.cx(0, 1)

    # 2) Alice encodes
    if bits == "00":
        pass
    elif bits == "01":
        qc.z(0)
    elif bits == "10":
        qc.x(0)
    else:  # "11"
        qc.x(0)
        qc.z(0)

    # 3) Bob decodes
    qc.cx(0, 1)
    qc.h(0)

    # 4) Measure
    qc.measure([0, 1], [0, 1])

    backend = Aer.get_backend("qasm_simulator")
    compiled_circuit = transpile(qc, backend)
    job = backend.run(compiled_circuit, shots=shots)
    result = job.result()
    counts = result.get_counts()

    # Find most likely string
    decoded = max(counts.items(), key=lambda kv: kv[1])[0]

    # Artifacts
    circ_b64 = circuit_png(qc)
    hist_b64 = histogram_png(counts)

    # Success rate ~ fraction of target bits
    success = counts.get(bits, 0) / shots

    return {
        "input_bits": bits,
        "decoded_bits": decoded,
        "counts": counts,
        "success_rate": success,
        "shots": shots,
        "circuit_png_base64": circ_b64,
        "histogram_png_base64": hist_b64,
    }

@app.post("/api/send")
def send(req: SendReq):
    try:
        out = superdense(req.bits, req.shots)
        return {"ok": True, "data": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}
