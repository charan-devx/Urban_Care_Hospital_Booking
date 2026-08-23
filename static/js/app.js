document.addEventListener("DOMContentLoaded", function () {

    const dateInput =
        document.getElementById("appointment_date");

    const timeSelect =
        document.getElementById("appointment_time");


    if (!dateInput || !timeSelect) {
        return;
    }


    dateInput.addEventListener(
        "change",
        async function () {

            const selectedDate =
                dateInput.value;


            if (!selectedDate) {

                timeSelect.innerHTML =
                    '<option value="">Select a date first</option>';

                return;
            }


            timeSelect.innerHTML =
                '<option value="">Loading available times...</option>';


            /*
             * URL example:
             *
             * /doctors/1/book
             *
             * We get doctor ID from the URL.
             */

            const pathParts =
                window.location.pathname
                    .split("/")
                    .filter(Boolean);


            const doctorId =
                pathParts[1];


            try {

                const response = await fetch(
                    `/api/doctors/${doctorId}/availability?date=${selectedDate}`
                );


                if (!response.ok) {

                    throw new Error(
                        "Failed to load availability"
                    );

                }


                const data =
                    await response.json();


                timeSelect.innerHTML =
                    '<option value="">Select a time</option>';


                /*
                 * Doctor is not working
                 * on selected day
                 */

                if (!data.available) {

                    const option =
                        document.createElement("option");


                    option.value = "";


                    option.textContent =
                        "Doctor is not available on this day";


                    timeSelect.appendChild(option);

                    return;
                }


                /*
                 * No free slots
                 */

                if (
                    !data.slots ||
                    data.slots.length === 0
                ) {

                    const option =
                        document.createElement("option");


                    option.value = "";


                    option.textContent =
                        "No available slots";


                    timeSelect.appendChild(option);

                    return;
                }


                /*
                 * Add available slots
                 */

                data.slots.forEach(
                    function (slot) {

                        const option =
                            document.createElement(
                                "option"
                            );


                        option.value =
                            slot.value;


                        option.textContent =
                            slot.display;


                        timeSelect.appendChild(
                            option
                        );

                    }
                );

            }


            catch (error) {

                console.error(
                    "Error loading availability:",
                    error
                );


                timeSelect.innerHTML =
                    '<option value="">Unable to load times</option>';

            }

        }
    );

});