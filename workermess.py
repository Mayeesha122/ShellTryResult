import os
import requests
import time
import subprocess
from urllib.parse import urlparse
import werkzeug.http
import base64

# Define the get_filename function
def get_filename(url: str, headers: dict):
    try:
        if content_disposition := headers.get("Content-Disposition"):
            param, options = werkzeug.http.parse_options_header(content_disposition)
            if param == 'attachment' and (filename := options.get('filename')):
                return filename

        path = urlparse(url).path
        name = os.path.basename(path)
        return name
    except Exception as e:
        print(f"Error while getting filename: {e}")
        return None

# URL of the Flask server
server_url = "http://10.5.52.126:5000"  # Replace with the actual IP address and port where Flask is running
least_recent_request_endpoint = "/api/least_recent_file"
request_transfer_endpoint = "/request_transfer"
tvla_completed_endpoint = "/tvla_completed"  # Endpoint to notify Flask server about TVLA completion
#worker_endpoint = "/worker"  # Endpoint to send result data back to Flask server
upload_results_endpoint = "/upload_results" # Endpoint to send result data back to Flask server(added)

# Base directory for result files
base_result_directory = "C:/workFinal/shellTry/data"

# Create the download directory if it doesn't exist
os.makedirs(base_result_directory, exist_ok=True)


while True:
    # Send a GET request to the server to retrieve information about the least recent request
    response = requests.get(server_url + least_recent_request_endpoint)

    if response.status_code == 200:
        try:
            least_recent_request_data = response.json()
            request_id = least_recent_request_data['least_recent_request']['id']
            file_ids = least_recent_request_data['least_recent_request']['file_ids']
            # Extract user_id from the least_recent_request_data (added)
            user_id = least_recent_request_data['least_recent_request']['user_id']

            print(f"Processing least recent request with ID:{request_id} of user:{user_id} ")

            # Fetch the file information for the associated file IDs
            file_info_list = []

            if file_ids:
                for file_id in file_ids.split(','):
                    download_endpoint = f"/download/{file_id}"
                    file_response = requests.get(server_url + download_endpoint, stream=True)

                    if file_response.status_code == 200:
                        filename = get_filename(file_response.url, file_response.headers)
                        upload_date = file_response.headers.get('Date')

                        print(f"Downloading file Id: {file_id} and name: {filename} (uploaded on {upload_date})")

                        # Create a folder for the current request ID for downloading files
                        request_folder_path = f'C:/workFinal/shellTry/FlaskWebsite/downloads/Request_{request_id}'
                        os.makedirs(request_folder_path, exist_ok=True) # Create the directory if it doesn't exist

                        # Save the downloaded file to the request-specific folder
                        file_path = os.path.join(request_folder_path, filename)
                        with open(file_path, 'wb') as f:
                            for chunk in file_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        print(f"File {filename} downloaded successfully to {request_folder_path}.")

                        # Add file information to the list
                        file_info_list.append({
                            'id': file_id,
                            'filename': filename,
                            'upload_date': upload_date,
                            'path': file_path
                        })

                        # Now, send a POST request to update the status to "Running" for the processed file
                        update_status_endpoint = f"/update_status/{request_id}"
                        status_data = {"status": "Running"}
                        status_response = requests.post(server_url + update_status_endpoint, json=status_data)

                        if status_response.status_code == 200:
                            print(f"Status of file {filename} updated to 'Running'.")
                        else:
                            print(f"Failed to update status of file {filename}. Server returned status code {status_response.status_code}.")
                    else:
                        print(f"Failed to download file with ID {file_id}. Server returned status code {file_response.status_code}.")
                print("please work")

                # Check for requests with a status of "Running"
                running_requests_response = requests.get(server_url + request_transfer_endpoint)

                if running_requests_response.status_code == 200:
                    running_requests_data = running_requests_response.json()
                    request_transfer_info = running_requests_data.get('request_transfer')
                    if request_transfer_info:
                        # Get the file_info list from the response JSON
                        file_info_list = request_transfer_info.get('file_info', [])

                        # Process files from the file_info list
                        for file_info in file_info_list:
                            file_id = file_info['id']
                            filename = file_info['filename']
                            request_id = file_info['request_id']  # added

                            # Perform your processing logic for the file with file_id and filename
                            print(f"Processing file ID: {file_id}, Filename: {filename}")
                            print(f"Processing Request ID: {request_id}")  # added

                        # Now, you can transfer the files specified in file_info list
                        print(f"Transferring files: {file_info_list}")

                        # Specify the bitstream and elf file paths

                        temp_filename = file_info_list[0]['filename']
                        if temp_filename.find('.bit') != -1:
                            bitstream_path = f'C:/workFinal/shellTry/FlaskWebsite/downloads/Request_{request_id}/{temp_filename}'
                        # bitstream_file = r"C:/workFinal/Masked/Kyber512_INDCCA2_Masked-main/Kyber512_CCAKEM_Masked.runs/impl_6/kyber_soc_wrapper.bit"
                        temp_filename = file_info_list[1]['filename']
                        if temp_filename.find('.elf') != -1:
                            elf_path = f'C:/workFinal/shellTry/FlaskWebsite/downloads/Request_{request_id}/{temp_filename}'

                        # Since Xilinx stuff uses Linux style files
                        bitstream_path = bitstream_path.replace('\\', '/')
                        elf_path = elf_path.replace('\\', '/')

                        print(f"bitstream_path to be passed as arg: {bitstream_path}")
                        print(f"Elf_path to be passed as arg: {elf_path}")
                        print(f"Request Id to be passed as arg: {request_id}")

                        # Run the Comb script
                        subprocess.run(['cmd', '/c', 'python', 'TVLA_hardware\comb.py', bitstream_path, elf_path, str(request_id)])
                        print("Comb script executed.")

                        # TVLA process completed, send a notification to the Flask server
                        tvla_payload = {
                            'request_id': request_id
                        }
                        tvla_response = requests.post(server_url + tvla_completed_endpoint, json=tvla_payload)

                        if tvla_response.status_code == 200:
                            print("TVLA processing completed. Notified the server.")
                        else:
                            print(f"Failed to notify server. Server returned status code {tvla_response.status_code}.")

                        ##Function to read and encode a file to base64
                        def file_to_base64(file_path):
                            with open(file_path, "rb") as file:
                                encoded_string = base64.b64encode(file.read()).decode("utf-8")
                                return encoded_string

                        # After processing the result files, create a dictionary with request_id and result_files -> ADDED
                        result_files = []
                        result_directory = os.path.join(base_result_directory, f"{request_id}_Poly_tomsg_unmasked_10_vccbram_VCC")
                        for root, dirs, files in os.walk(result_directory):
                          for file in files:
                            result_files.append(os.path.join(root, file))

                        result_data = {
                            "user_id": user_id,
                            'request_id': request_id,
                            'result_files': result_files,
                            'files': []  # List to store file data (filename and content)
                        }

                        #prepare and add files data to the result_data
                        for file_path in result_files:
                            file_name = os.path.basename(file_path)
                            file_content_base64 = file_to_base64(file_path)
                            result_data['files'].append({
                                'filename': file_name,
                                'content': file_content_base64
                            })
                        # Send data to Flask application using HTTP POST request
                        url = "http://10.5.52.126:5000/upload_results"  # My Flask app URL
                        headers = {'Content-Type': 'application/json'}
                        response = requests.post(url, json=result_data, headers=headers)

                        # # After processing the result files, create a dictionary with request_id and result_files
                        # result_files = []
                        # result_directory = os.path.join(base_result_directory, f"{request_id}_Poly_tomsg_unmasked_10_vccbram_VCC")
                        # for root, dirs, files in os.walk(result_directory):
                        #     for file in files:
                        #         result_files.append(os.path.join(root, file))

                        # result_data = {
                        #     "user_id": user_id,
                        #     'request_id': request_id,
                        #     'result_files': result_files,
                        #     'files': [] #adding files to json
                        # }

                        # #numpy path
                        # file_name1 = result_files[0]

                        # #png path
                        # file_name2 = result_files[1]

                        # with open(file_name1) as f1, open(file_name2) as f2:
                        #     result_data['files'].append({file_name1, f1})
                        #     result_data['files'].append({file_name2, f2})

                        # Send the result data to the Flask server
                        # try:
                        #     result_response = requests.post(server_url + upload_results_endpoint, json=result_data)

                        #     if result_response.status_code == 200:
                        #      print("Result data sent to the server.")
                        #     else:
                        #      print(f"Failed to send result data to the server. Server returned status code {result_response.status_code}.")

                        # except Exception as e:
                        #    print(f"Error: {e}")
        except Exception as ee:
                           print(f"An error occurred: {ee}")

    else:
        print(f"Failed to retrieve information about the least recent request or received an error response from the server. Server returned status code {response.status_code}.")

    # Sleep for 3 minutes before checking for new requests again
    time.sleep(180)
