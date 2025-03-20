from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import pandas as pd
import os
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg
import matplotlib.pyplot as plt
import seaborn as sns
import uuid
import plotly.express as px
import plotly.io as pio
import json
import numpy as np
from datetime import datetime
from io import BytesIO
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/reports', exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_column_name(col_name):
    """Clean column names from unwanted characters"""
    if isinstance(col_name, str):
        return re.sub(r'[^\w\s]', '', col_name).strip().replace(' ', '_')
    return f'column_{col_name}'

def process_file(filepath):
    """Process and analyze the data file"""
    file_ext = filepath.rsplit('.', 1)[1].lower()
    
    try:
        if file_ext == 'csv':
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
            
        # Clean column names
        df.columns = [clean_column_name(col) for col in df.columns]
        
        # Save processed data to a temporary file
        processed_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv')
        df.to_csv(processed_filepath, index=False)
        
        # Descriptive statistics
        stats = df.describe(include='all').fillna('').to_html(classes='table table-striped table-hover')
        
        # Extract file information
        file_info = {
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': df.columns.tolist(),
            'missing_data': df.isna().sum().sum(),
            'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB"
        }
        
        # Identify numeric columns for plots
        numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Generate distribution plot using seaborn
        if numeric_columns:
            # Plot distribution of a numeric column
            plt.figure(figsize=(10, 6))
            sns.set_style("whitegrid")
            ax = sns.histplot(df[numeric_columns[0]], kde=True, color='skyblue')
            ax.set_title(f'Distribution of {numeric_columns[0]}', fontsize=16)
            ax.set_xlabel(numeric_columns[0], fontsize=12)
            ax.set_ylabel('Frequency', fontsize=12)
            plt.tight_layout()
            
            hist_path = os.path.join(app.config['UPLOAD_FOLDER'], 'histogram.png')
            plt.savefig(hist_path, dpi=100, bbox_inches='tight')
            plt.close()
            
            # Plot scatter plot if more than one numeric column exists
            if len(numeric_columns) > 1:
                plt.figure(figsize=(10, 6))
                sns.scatterplot(data=df, x=numeric_columns[0], y=numeric_columns[1], 
                                hue=categorical_columns[0] if categorical_columns else None)
                plt.title(f'Relationship between {numeric_columns[0]} and {numeric_columns[1]}', fontsize=16)
                plt.xlabel(numeric_columns[0], fontsize=12)
                plt.ylabel(numeric_columns[1], fontsize=12)
                plt.tight_layout()
                
                scatter_path = os.path.join(app.config['UPLOAD_FOLDER'], 'scatter.png')
                plt.savefig(scatter_path, dpi=100, bbox_inches='tight')
                plt.close()
            else:
                scatter_path = None
            
            # Generate box plot using Plotly
            fig = px.box(df, y=numeric_columns[0:min(len(numeric_columns), 5)])
            fig.update_layout(
                title=f"Box Plot of Numeric Columns",
                title_font_size=20,
                height=500,
                template="plotly_white"
            )
            
            boxplot_path = os.path.join(app.config['UPLOAD_FOLDER'], 'boxplot.json')
            with open(boxplot_path, 'w') as f:
                f.write(json.dumps(fig.to_json()))
        else:
            hist_path = None
            scatter_path = None
            boxplot_path = None
        
        # Create a pie chart for categorical data if available
        if categorical_columns:
            cat_col = categorical_columns[0]
            value_counts = df[cat_col].value_counts().nlargest(10)
            
            plt.figure(figsize=(10, 6))
            plt.pie(value_counts, labels=value_counts.index, autopct='%1.1f%%', 
                    startangle=90, shadow=True, explode=[0.05] * len(value_counts))
            plt.title(f'Distribution of {cat_col}', fontsize=16)
            plt.axis('equal')
            
            pie_path = os.path.join(app.config['UPLOAD_FOLDER'], 'piechart.png')
            plt.savefig(pie_path, dpi=100, bbox_inches='tight')
            plt.close()
        else:
            pie_path = None
        
        return {
            'stats': stats, 
            'file_info': file_info, 
            'numeric_columns': numeric_columns,
            'categorical_columns': categorical_columns,
            'plots': {
                'histogram': 'histogram.png' if hist_path else None,
                'scatter': 'scatter.png' if scatter_path else None,
                'boxplot': 'boxplot.json' if boxplot_path else None,
                'piechart': 'piechart.png' if pie_path else None
            }
        }
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file found', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Generate a unique filename
                filename = f"{str(uuid.uuid4())}_{file.filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Process the file
                results = process_file(filepath)
                
                if results:
                    return render_template(
                        'results.html', 
                        stats=results['stats'], 
                        file_info=results['file_info'],
                        plots=results['plots'],
                        numeric_columns=results['numeric_columns'],
                        categorical_columns=results['categorical_columns']
                    )
                else:
                    flash('Error processing file', 'danger')
                    return redirect(request.url)
            except Exception as e:
                flash(f'Error: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('File type not allowed. Please use CSV or Excel files', 'warning')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/filter', methods=['POST'])
def filter_data():
    """Filter data based on specified criteria"""
    try:
        processed_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv')
        
        if not os.path.exists(processed_filepath):
            return jsonify({'error': 'No processed data found'}), 400
        
        df = pd.read_csv(processed_filepath)
        
        column = request.form.get('column')
        operation = request.form.get('operation')
        value = request.form.get('value')
        
        if not all([column, operation, value]):
            return jsonify({'error': 'Incomplete filter information'}), 400
        
        # Convert value to appropriate type
        if column in df.select_dtypes(include=['int64', 'float64']).columns.tolist():
            try:
                value = float(value)
            except ValueError:
                return jsonify({'error': 'Invalid numeric value'}), 400
        
        # Apply filter operation
        if operation == 'equals':
            filtered_df = df[df[column] == value]
        elif operation == 'contains':
            filtered_df = df[df[column].astype(str).str.contains(str(value), na=False)]
        elif operation == 'greater_than':
            filtered_df = df[df[column] > value]
        elif operation == 'less_than':
            filtered_df = df[df[column] < value]
        else:
            return jsonify({'error': 'Invalid filter operation'}), 400
        
        # Generate HTML for filtered data table
        table_html = filtered_df.head(50).to_html(classes='table table-striped table-hover')
        
        return jsonify({
            'html': table_html,
            'count': len(filtered_df),
            'total': len(df)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<format>', methods=['GET'])
def download_report(format):
    """Download data in specified format"""
    try:
        processed_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv')
        
        if not os.path.exists(processed_filepath):
            flash('No processed data found', 'danger')
            return redirect(url_for('index'))
            
        df = pd.read_csv(processed_filepath)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'csv':
            # Export as CSV file
            output = BytesIO()
            df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            
            return send_file(
                output,
                as_attachment=True,
                download_name=f'data_report_{timestamp}.csv',
                mimetype='text/csv'
            )
        
        elif format == 'excel':
            # Export as Excel file
            output = BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)
            
            return send_file(
                output,
                as_attachment=True,
                download_name=f'data_report_{timestamp}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        else:
            flash('Invalid format', 'danger')
            return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/generate_plot', methods=['POST'])
def generate_plot():
    """Generate custom plots"""
    try:
        plot_type = request.form.get('plot_type')
        x_axis = request.form.get('x_axis')
        y_axis = request.form.get('y_axis')
        
        if not all([plot_type, x_axis, y_axis]):
            return jsonify({'error': 'Incomplete plot information'}), 400
            
        processed_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_data.csv')
        df = pd.read_csv(processed_filepath)
        
        plot_id = f"custom_plot_{uuid.uuid4()}.png"
        plot_path = os.path.join(app.config['UPLOAD_FOLDER'], plot_id)
        
        plt.figure(figsize=(10, 6))
        
        if plot_type == 'scatter':
            plt.scatter(df[x_axis], df[y_axis], alpha=0.7)
            plt.title(f'Scatter Plot: {x_axis} vs {y_axis}')
        
        elif plot_type == 'line':
            plt.plot(df[x_axis], df[y_axis])
            plt.title(f'Line Plot: {x_axis} vs {y_axis}')
        
        elif plot_type == 'bar':
            plt.bar(df[x_axis].head(20), df[y_axis].head(20))
            plt.title(f'Bar Plot: {x_axis} vs {y_axis}')
            plt.xticks(rotation=45)
        
        plt.xlabel(x_axis)
        plt.ylabel(y_axis)
        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close()
        
        return jsonify({'success': True, 'plot_url': f'/static/uploads/{plot_id}'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)