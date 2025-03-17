import {select, on} from "../helpers.js";


export const BootstrapPassword = (() => {

  const togglePasswordVisibility = () => {
    const icon = select('.password-view-toggle');
    const password = icon.previousElementSibling;

    const showPassword = password.getAttribute("type") === "password";
    password.setAttribute("type", showPassword ? "text" : "password");
    icon.firstElementChild.classList.toggle("fa-eye-slash", showPassword === false);
    icon.firstElementChild.classList.toggle("fa-eye", showPassword === true);

  }

  const scoreStrength = (password) => {
    let strength = 0;
    let targetLength = 8;  // Preferably 12 characters or more
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++;
    strength += Math.min(Math.floor(password.length / (targetLength / 4)), 4);  // Up to 4 points for length
    return strength;
  }

  const strengthChecker = () => {
    const strengthBar = select('.strength-bar');
    const icon = select('.password-view-toggle');
    const password = icon.previousElementSibling;
    const passwordValue = password.value;

    let maxStrength = 8;
    let strength = scoreStrength(passwordValue);

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
    scoreStrength,
    strengthChecker
  };
})();