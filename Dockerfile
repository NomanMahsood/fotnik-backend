# Step 1: Use a Python base image
FROM python:3.9-slim

# Step 2: Set the working directory in the container
WORKDIR /app

# Step 3: Install Miniconda
RUN apt-get update && apt-get install -y curl \
    && curl -sSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh \
    && bash miniconda.sh -b -f -p /opt/conda \
    && rm miniconda.sh

# Step 4: Add Conda to PATH
ENV PATH /opt/conda/bin:$PATH

# Step 5: Copy your project files into the container
COPY . /app

# Step 6: Install dependencies using the environment.yml file
RUN conda env create -f environment.yml

# Step 7: Activate the Conda environment and install additional dependencies
SHELL ["conda", "run", "-n", "fotnik", "/bin/bash", "-c"]
RUN conda install -n fotnik pip \
    && pip install uvicorn stripe

# Step 8: Expose the port your app runs on (port 8010)
EXPOSE 8010

# Step 9: Set the default command to run your app
CMD ["conda", "run", "--no-capture-output", "-n", "fotnik", "python", "main.py"]
