import pickle
from pathlib import Path

import gradio as gr
from sklearn.pipeline import Pipeline

HERE = Path(__file__).parent

# Load the trained model and scaler
with open(HERE / "cars24_model.pkl", "rb") as f:
    model = pickle.load(f)

with open(HERE / "scaler.pkl", "rb") as f:
    scaler = pickle.load(f)

# Create a pipeline that combines scaling and prediction
pipeline = Pipeline([("scaler", scaler), ("model", model)])


encode_dict = {
    "fuel_type": {"Diesel": 1, "Petrol": 2, "CNG": 3, "LPG": 4, "Electric": 5},
    "transmission_type": {"Manual": 1, "Automatic": 2},
    "seller_type": {"Dealer": 1, "Individual": 2, "Trustmark Dealer": 3},
}


def model_pred(
    year,
    seller_type,
    km_driven,
    fuel_type,
    transmission_type,
    mileage,
    engine,
    max_power,
    seats,
):
    # Convert categorical features using the encode dictionary
    seller_type_enc = encode_dict["seller_type"][seller_type]
    fuel_type_enc = encode_dict["fuel_type"][fuel_type]
    transmission_type_enc = encode_dict["transmission_type"][transmission_type]

    # Prepare input data
    data = [
        [
            float(year),
            seller_type_enc,
            float(km_driven),
            fuel_type_enc,
            transmission_type_enc,
            float(mileage),
            float(engine),
            float(max_power),
            float(seats),
        ]
    ]

    # Use pipeline for prediction (handles scaling automatically)
    prediction = pipeline.predict(data)

    # float() first: the model returns float32, which round() can't clean up
    return round(float(prediction[0]), 2)


def predict(
    year,
    seller_type,
    fuel_type,
    max_power,
    engine,
    km_driven,
    mileage,
    transmission_type,
    seats,
):
    price = model_pred(
        year,
        seller_type,
        km_driven,
        fuel_type,
        transmission_type,
        mileage,
        engine,
        max_power,
        seats,
    )

    return f"**Predicted Car Price**: {price} Lakhs (approx.)"


with gr.Blocks(title="Cars24 Used Car Price Prediction") as demo:
    gr.Markdown("# Cars24 Used Car Price Prediction")

    year = gr.Slider(
        minimum=1990, maximum=2023, value=2015, step=1, label="Manufacturing Year"
    )
    seller_type = gr.Dropdown(
        ["Dealer", "Individual", "Trustmark Dealer"],
        value="Dealer",
        label="Seller Type",
    )

    with gr.Row():
        with gr.Column():
            fuel_type = gr.Dropdown(
                ["Diesel", "Petrol", "CNG", "LPG", "Electric"],
                value="Diesel",
                label="Fuel Type",
            )
            max_power = gr.Number(
                minimum=0.0, maximum=300.0, value=150.0, step=5.0,
                label="Max Power (bhp)",
            )

        with gr.Column():
            engine = gr.Number(
                minimum=500, maximum=5000, value=1500, step=100, label="Engine (cc)"
            )
            km_driven = gr.Number(
                minimum=0, maximum=1000000, value=50000, step=5000,
                label="Kilometers Driven",
            )

    mileage = gr.Number(
        minimum=0.0, maximum=18.0, value=15.0, step=0.5, label="Mileage (kmpl)"
    )

    transmission_type = gr.Dropdown(
        ["Manual", "Automatic"], value="Manual", label="Transmission Type"
    )

    seats = gr.Number(minimum=2, maximum=10, value=5, step=1, label="Seats")

    output = gr.Markdown("Click the **Predict** button once you've entered all the details.")

    gr.Button("Predict", variant="primary").click(
        fn=predict,
        inputs=[
            year,
            seller_type,
            fuel_type,
            max_power,
            engine,
            km_driven,
            mileage,
            transmission_type,
            seats,
        ],
        outputs=output,
    )


if __name__ == "__main__":
    # share=True also gives a temporary public https://....gradio.live URL
    demo.launch()
