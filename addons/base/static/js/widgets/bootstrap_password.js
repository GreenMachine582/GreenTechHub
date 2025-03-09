import {select, on} from "../helpers.js";


export const BootstrapPassword = (() => {

  const togglePasswordVisibility = () => {
    const icon = select('.password-view-toggle');
    const password = icon.previousElementSibling;

    const showPassword = password.getAttribute("type") === "password";
    if (showPassword) {
      password.setAttribute("type", "text");
    } else {
      password.setAttribute("type", "password");
    }
    icon.firstElementChild.classList.toggle("fa-eye-slash", showPassword === false);
    icon.firstElementChild.classList.toggle("fa-eye", showPassword === true);

  }

  const strengthChecker = () => {
    const strengthBar = select('.strength-bar');
    const icon = select('.password-view-toggle');
    const password = icon.previousElementSibling;
    const passwordValue = password.value;

    let maxStrength = 8;
    let strength = 0;
    let minLength = 12;  // Preferably 12 characters or more
    if (/[A-Z]/.test(passwordValue)) strength++;
    if (/[a-z]/.test(passwordValue)) strength++;
    if (/\d/.test(passwordValue)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(passwordValue)) strength++;
    strength += Math.min(Math.floor(passwordValue.length / (minLength / 4)), 4);  // Up to 4 points for length

    const strengthBarMeter = strengthBar.firstElementChild;
    strengthBarMeter.style.width = `${strength * (100 / maxStrength)}%`;
    // Apply background-color based on strength
    const red = Math.max(0, 255 - Math.round((strength / maxStrength) * 255));
    const green = Math.min(200, Math.round(((strength - 2) / maxStrength) * 255));
    strengthBarMeter.style.backgroundColor = `rgb(${red}, ${green}, 0)`;

  }

  const init = () => {

    /**
     * Click Password Toggle Event
     */

    if (select('.password-view-toggle')) {
      on('click', '.password-view-toggle', togglePasswordVisibility)
    }

    /**
     * Input Password Event
     */

    if (select('.password-container input')) {
      on('input', '.password-container input', strengthChecker)
    }
  }

  return {
    init,
    togglePasswordVisibility,
    strengthChecker
  };
})();