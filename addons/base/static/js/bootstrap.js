
import {BootstrapPassword} from "./widgets/bootstrap_password.js";
import {on} from "./helpers.js";

export const Bootstrap = (() => {
  /**
   * Validate form inputs
   */

  const widgets = {
    Password: BootstrapPassword
  }

  const validateInput = (input) => {
    let isValid;

    // Apply custom widget validation
    if (input.matches('.password-container input')) {
      isValid = (BootstrapPassword.scoreStrength(input.value) >= 8);
    } else if (input.type === "email") {
      const emailPattern = /^[A-Z0-9._%+-]+@((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+)(?:[A-Z0-9-]{2,63}(?<!-))$/i;
      isValid = emailPattern.test(input.value);
    } else {
      isValid = input.checkValidity(); // Use built-in HTML validation
    }

    // Toggle Bootstrap's validation classes
    input.classList.toggle("is-valid", isValid);
    input.classList.toggle("is-invalid", !isValid);

    // if (input.form) {
    //   input.form.classList.add("was-validated");
    // }
    return isValid;
  }

  const validateInputEvent = (e) => {
    validateInput(e.target);
  }

  const validateForm = () => {
    // Fetch all the forms we want to apply custom Bootstrap validation styles to
    const forms = document.querySelectorAll('.needs-validation');

    const bootstrapValidate = (form) => {
      let isValid = true;

      form.querySelectorAll('input.form-control').forEach((input) => {
        isValid = validateInput(input) && isValid;
      });

      return isValid;
    }

    // Loop over them and prevent submission
    forms.forEach(function (form) {
      form.addEventListener('submit', function (event) {
        if (!form.checkValidity() || !bootstrapValidate(form)) {
          event.preventDefault();
          event.stopPropagation();
        }

      }, false);
    });
  }

  const init = () => {
    document.addEventListener("DOMContentLoaded", function () {
      on("input", "input.form-control", validateInputEvent, true);

      validateForm();
    });

    /**
     * Initialise Bootstrap Widgets
     */
    for (let widget in widgets) {
      if (widgets.hasOwnProperty(widget)) {
        widgets[widget].init();
      }
    }
  }

  return {
    init,
    validateInput,
    widgets
  }

})();
