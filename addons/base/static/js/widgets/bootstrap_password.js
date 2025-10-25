import {select, on} from "../helpers.js";


export const BootstrapPassword = (() => {
  let bound = false; // avoid double-binding

  const findContainer = (el) => el?.closest?.(".password-container");

  const togglePasswordVisibility = (btn) => {
    const container = findContainer(btn);
    if (!container) return;
    const input = container.querySelector("input");
    if (!input) return;

    const show = input.getAttribute("type") === "password";
    input.setAttribute("type", show ? "text" : "password");

    const icon = btn.querySelector("i");
    if (icon) {
      icon.classList.toggle("fa-eye",  show);
      icon.classList.toggle("fa-eye-slash", !show);
    }
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

  const updateStrengthBar = (input) => {
    const container = findContainer(input);
    if (!container) return;
    const bar = container.querySelector(".strength-bar > *"); // inner meter element
    if (!bar) return;

    const max = 8;
    const val = scoreStrength(input.value);
    bar.style.width = `${(val / max) * 100}%`;

    // simple color gradient
    const red = Math.max(0, 255 - Math.round((val / max) * 255));
    const green = Math.min(200, Math.round(((val - 2) / max) * 255));
    bar.style.backgroundColor = `rgb(${red}, ${green}, 0)`;
  };

  // const strengthChecker = () => {
  //   const strengthBar = select('.strength-bar');
  //   const icon = select('.password-view-toggle');
  //   const password = icon.previousElementSibling;
  //   const passwordValue = password.value;
  //
  //   let maxStrength = 8;
  //   let strength = scoreStrength(passwordValue);
  //
  //   const strengthBarMeter = strengthBar.firstElementChild;
  //   strengthBarMeter.style.width = `${strength * (100 / maxStrength)}%`;
  //   // Apply background-color based on strength
  //   const red = Math.max(0, 255 - Math.round((strength / maxStrength) * 255));
  //   const green = Math.min(200, Math.round(((strength - 2) / maxStrength) * 255));
  //   strengthBarMeter.style.backgroundColor = `rgb(${red}, ${green}, 0)`;
  //
  // }

  const ensureScaffold = (root = document) => {
    select(root.querySelectorAll?.(".password-container") || [], true).forEach((wrap) => {
      // Toggle button
      if (!wrap.querySelector(".password-view-toggle")) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-outline-secondary password-view-toggle ms-2";
        btn.innerHTML = '<i class="fa-solid fa-eye"></i>';
        // Place after input (or at end)
        const input = wrap.querySelector("input");
        if (input?.parentNode) {
          input.parentNode.insertBefore(btn, input.nextSibling);
        } else {
          wrap.appendChild(btn);
        }
      }
      // Strength bar
      if (!wrap.querySelector(".strength-bar")) {
        const bar = document.createElement("div");
        bar.className = "strength-bar mt-2";
        bar.innerHTML = '<div style="height:6px;width:0;"></div>';
        wrap.appendChild(bar);
      }
    });
  };

  const initDelegated = () => {
    if (bound) return;
    bound = true;

    // Toggle visibility (delegated)
    on("click", document, (e) => {
      const btn = e.target.closest(".password-view-toggle");
      if (!btn) return;
      togglePasswordVisibility(btn);
    });

    // Strength meter (delegated)
    on("input", document, (e) => {
      const input = e.target.closest?.(".password-container input");
      if (!input) return;
      updateStrengthBar(input);
    });
  };

  const init = (root = document) => {
    initDelegated();      // set up once on document
    ensureScaffold(root); // add missing UI bits inside root (page or modal)
    // initial paint for existing inputs
    select(root.querySelectorAll?.(".password-container input") || [], true)
      .forEach(updateStrengthBar);
  };

  // For explicit modal usage if you want (same as init(root))
  const initIn = (root) => init(root);

  return {
    init,
    initIn,
    scoreStrength,
  };
})();