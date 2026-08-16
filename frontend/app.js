// app.js

// Get the "Get Results" button and add a click event listener
document.getElementById("getResults").addEventListener("click", function () {
  // Get the assignment request ID from the input field
  const assignmentRequestId = document.getElementById("assignmentID").value;

  // Check if the input field is empty
  if (!assignmentRequestId) {
    alert("Please enter an Assignment Request ID.");
    return;
  }

  // Show a loading message while waiting for the response
  document.getElementById("result").innerHTML = "Loading... Please wait...";

  // Fetch the assignment summary from the backend API
  fetch(`http://localhost:5000/api/request/${assignmentRequestId}/summary`)
    .then(response => {
      // Check if the response is ok (status code 200)
      if (!response.ok) {
        throw new Error("Failed to fetch data from the server");
      }
      return response.json(); // Parse the JSON response
    })
    .then(data => {
      // Process the data and update the UI with summary details
      document.getElementById("result").innerHTML = `
        <p>No of drivers: ${data.counts.drivers}</p>
        <p>No of DriverSchedules: ${data.counts.schedules}</p>
        <p>No of Bookings: ${data.counts.bookings}</p>
        <p>Total Assignments Generated: ${data.counts.assignments}</p>
      `;
      
      // After fetching the summary, trigger the backend to process and generate the assignments
      triggerAssignmentGeneration(assignmentRequestId);
    })
    .catch(error => {
      // Display an error message in case of failure
      console.error('Error fetching results:', error);
      document.getElementById("result").innerHTML = "An error occurred while fetching data.";
    });
});

// Function to trigger assignment generation (POST request to /process)
function triggerAssignmentGeneration(assignmentRequestId) {
  // Fetch the process endpoint to trigger assignment generation
  fetch(`http://localhost:5000/api/request/${assignmentRequestId}/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({}) // Add any necessary body data if required
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Failed to process the request');
    }
    return response.json();
  })
  .then(data => {
    console.log('Assignments processed:', data);
    alert('Assignments generated successfully!');
  })
  .catch(error => {
    console.error('Error processing assignments:', error);
    alert('An error occurred while generating assignments.');
  });
}
