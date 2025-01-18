import streamlit as st
import pandas as pd
from pyairtable import Api
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pytz

# Airtable Konfiguration
AIRTABLE_API_KEY = 'pat6k3Xcf9cw1svUE.047ecff2db78aaf279e45197e3f7b8bbc2f1694b6fd950e5798ea5ea3e0747f5'
AIRTABLE_BASE_ID = 'app6AAzaxp41FlLUY'
PRICE_TABLE_ID = 'tblOsWyMnECDnHQmN'
FEEDBACK_TABLE_ID = 'tbl1dpQ06D46OIKt7'

class AirtableManager:
    def __init__(self):
        self.api = Api(AIRTABLE_API_KEY)
        self.price_table = self.api.table(AIRTABLE_BASE_ID, PRICE_TABLE_ID)
        self.feedback_table = self.api.table(AIRTABLE_BASE_ID, FEEDBACK_TABLE_ID)
    
    def load_price_data(self):
        """Lädt die Preis-Daten aus der Price_Tracking Tabelle"""
        try:
            records = self.price_table.all()
            
            if not records:
                st.error("Keine Preis-Daten gefunden.")
                return pd.DataFrame()
                
            data = []
            for record in records:
                fields = record['fields']
                try:
                    # Extrahiere Datum und Zeit
                    date = fields.get('Date', '')
                    if isinstance(date, str):
                        # Behandle das Datum als naive datetime und konvertiere dann zu UTC
                        date_obj = pd.to_datetime(date.split('.')[0])  # Entferne Millisekunden falls vorhanden
                        if date_obj.tz is None:  # Nur lokalisieren wenn keine Zeitzone vorhanden
                            date_obj = date_obj.tz_localize('UTC')
                    else:
                        continue
                        
                    data.append({
                        'date': date_obj,
                        'price': float(fields.get('Price_USD', 0)),
                        'last_buy': float(fields.get('Last_Buy_Price', 0)),
                        'last_sell': float(fields.get('Last_Sell_Price', 0))
                    })
                except (ValueError, AttributeError) as e:
                    st.warning(f"Fehler beim Verarbeiten eines Datensatzes: {e}")
                    continue
            
            df = pd.DataFrame(data)
            if not df.empty:
                df.sort_values('date', inplace=True)
                
                # Debug-Info
                st.write("Datum Beispiel:", df['date'].iloc[0])
                st.write("Zeitzone:", df['date'].dt.tz)
                
            return df
            
        except Exception as e:
            st.error(f"Fehler beim Laden der Preis-Daten: {str(e)}")
            return pd.DataFrame()
    
    def submit_feedback(self, notes, status="Neu"):
        """Sendet Feedback an die Feedback-Tabelle"""
        try:
            current_time = datetime.now(pytz.UTC).isoformat()
            self.feedback_table.create({
                'Date': current_time,
                'Notes': notes,
                'Status': status
            })
            return True
        except Exception as e:
            st.error(f"Fehler beim Senden des Feedbacks: {str(e)}")
            return False

def main():
    st.set_page_config(page_title="BTC Price Tracking", layout="wide")
    
    st.title("🚀 Bitcoin Trading Dashboard")
    
    airtable_manager = AirtableManager()
    
    try:
        # Lade Daten
        with st.spinner('Lade Daten aus Airtable...'):
            df = airtable_manager.load_price_data()
        
        if df.empty:
            st.warning("Keine Daten verfügbar.")
            st.stop()
            
        # Zeitfilter
        col1, col2 = st.columns(2)
        with col1:
            hours = st.slider('Letzte Stunden anzeigen:', 1, 24, 4)
        
        # Filtere Daten nach ausgewähltem Zeitraum
        start_date = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=hours)
        filtered_df = df[df['date'] >= start_date].copy()
        
        if filtered_df.empty:
            st.warning(f"Keine Daten für den gewählten Zeitraum verfügbar.")
            st.stop()
            
        # Metriken anzeigen
        current_price = filtered_df['price'].iloc[-1]
        last_buy = filtered_df['last_buy'].iloc[-1]
        last_sell = filtered_df['last_sell'].iloc[-1]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Aktueller Preis", 
                     f"${current_price:,.2f}")
            
        with col2:
            buy_diff = ((current_price - last_buy) / last_buy * 100) if last_buy > 0 else 0
            st.metric("Letzter Kaufpreis", 
                     f"${last_buy:,.2f}",
                     f"{buy_diff:+.2f}%")
            
        with col3:
            if last_sell > 0:
                sell_diff = ((current_price - last_sell) / last_sell * 100)
                st.metric("Letzter Verkaufpreis", 
                         f"${last_sell:,.2f}",
                         f"{sell_diff:+.2f}%")

        # Chart erstellen
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=filtered_df['date'],
            y=filtered_df['price'],
            name='Aktueller Preis',
            line=dict(color='#17BECF')
        ))

        fig.add_hline(y=last_buy, 
                     line_dash="dash", 
                     line_color="green",
                     annotation_text="Letzter Kauf")
        
        if last_sell > 0:
            fig.add_hline(y=last_sell, 
                         line_dash="dash", 
                         line_color="red",
                         annotation_text="Letzter Verkauf")

        fig.update_layout(
            title='Bitcoin Preisentwicklung mit Trading-Levels',
            xaxis_title='Zeit',
            yaxis_title='Preis (USD)',
            height=600,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Feedback-Sektion
        st.markdown("---")
        st.header("📝 Feedback")
        
        with st.form("feedback_form"):
            feedback_text = st.text_area(
                "Ihr Feedback",
                placeholder="Teilen Sie uns Ihre Gedanken, Vorschläge oder Probleme mit...",
                height=100
            )
            
            submitted = st.form_submit_button("Feedback senden")
            
            if submitted and feedback_text.strip():
                if airtable_manager.submit_feedback(feedback_text):
                    st.success("Vielen Dank für Ihr Feedback! Es wurde erfolgreich übermittelt.")
                else:
                    st.error("Entschuldigung, beim Senden des Feedbacks ist ein Fehler aufgetreten.")

        # Debug Info
        if st.checkbox("Debug Info anzeigen"):
            st.write("Daten-Info:")
            st.write("Anzahl Datenpunkte:", len(df))
            st.write("Zeitraum:", df['date'].min(), "bis", df['date'].max())

    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {str(e)}")
        st.error("Details zum Debugging wurden in die Konsole geschrieben.")
        print(f"Detailed error: {str(e)}")

if __name__ == "__main__":
    main()