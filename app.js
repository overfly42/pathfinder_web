const tabs = document.querySelectorAll('.tab');
const viewContent = document.getElementById('view-content');

const views = {
  overview: `
    <h3>Character Overview</h3>
    <p>Kael is prepared for exploration, ranged combat, and tracking foes across the wilderness.</p>
    <ul class="list">
      <li>Current equipment is ready for travel and scouting.</li>
      <li>Combat values are focused on ranged attacks and survival.</li>
      <li>Level-up choices should improve ranged damage and utility.</li>
    </ul>
  `,
  inventory: `
    <h3>Inventory</h3>
    <ul class="list">
      <li>Traveler's Pack</li>
      <li>10 Arrows</li>
      <li>Healing Potion</li>
      <li>Rope and Grappling Hook</li>
      <li>Weathered Longbow</li>
    </ul>
  `,
  levelup: `
    <h3>Next Level</h3>
    <p>Choose a class, review new abilities, and confirm the upgrade for the next milestone.</p>
    <ul class="list">
      <li>Increase ranged combat effectiveness</li>
      <li>Improve survival and scouting tools</li>
      <li>Unlock a new class feature</li>
    </ul>
  `
};

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    tabs.forEach((item) => item.classList.remove('active'));
    tab.classList.add('active');
    viewContent.innerHTML = views[tab.dataset.view] || views.overview;
  });
});
