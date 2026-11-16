using System;
using System.Collections.Generic;
using System.Linq;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentSelectorsTests {
        private enum Category { OST_Walls = -2000011, OST_Doors = -2000023 }

        private sealed class View {
            public long Id;
            public string Name;
            public string Number;
        }

        private static readonly List<View> Views = new List<View> {
            new View { Id = 100, Name = "Level 1" },
            new View { Id = 101, Name = "Level 1" },
            new View { Id = 102, Name = "12345" },
            new View { Id = 103, Name = "Site" },
            new View { Id = 104, Name = "Roof Plan", Number = "A101" },
        };

        private static List<View> Find(string selector) =>
            AgentSelectors.FindView(selector, id => Views.FirstOrDefault(view => view.Id == id), Views, view => view.Name, view => view.Number);

        [Fact]
        public void AnIdFindsThatView() {
            Assert.Equal(new long[] { 103 }, Find("103").Select(view => view.Id));
        }

        [Fact]
        public void ADigitsOnlyNameThatIsNoViewIdIsFoundByName() {
            Assert.Equal(new long[] { 102 }, Find("12345").Select(view => view.Id));
        }

        [Fact]
        public void ASharedNameReturnsEveryMatch() {
            Assert.Equal(new long[] { 100, 101 }, Find("level 1").Select(view => view.Id));
        }

        [Fact]
        public void ASheetNumberFindsThatSheetIgnoringCase() {
            Assert.Equal(new long[] { 104 }, Find("a101").Select(view => view.Id));
        }

        [Fact]
        public void AnUnknownNameFindsNothing() {
            Assert.Empty(Find("Roof"));
        }

        [Theory]
        [InlineData("OST_Walls", true)]
        [InlineData("ost_doors", true)]
        [InlineData("OST_Walls,OST_Doors", false)]
        [InlineData("-2000011", false)]
        [InlineData("OST_Windows", false)]
        [InlineData("", false)]
        public void OnlyASingleDeclaredMemberParses(string name, bool parses) {
            Assert.Equal(parses, AgentSelectors.TryParseMember(name, out Category _));
        }

        [Fact]
        public void RepeatedCategoriesCountOnce() {
            var names = Enumerable.Repeat(new[] { "Walls", "OST_Doors", "walls" }, 40).SelectMany(group => group).ToList();
            Assert.Equal(120, names.Count);
            Assert.Equal(
                new[] { Category.OST_Walls, Category.OST_Doors },
                AgentSelectors.ParseDistinctCategories<Category>(names, 2));
        }

        [Fact]
        public void MoreDistinctCategoriesThanTheCapAreRefused() {
            var error = Assert.Throws<AgentException>(() =>
                AgentSelectors.ParseDistinctCategories<Category>(new[] { "Walls", "Doors" }, 1));
            Assert.Equal("invalid_params", error.Code);
        }

        [Fact]
        public void AnUnknownCategoryIsRefused() {
            var error = Assert.Throws<AgentException>(() =>
                AgentSelectors.ParseDistinctCategories<Category>(new[] { "Roofs" }, 5));
            Assert.Equal("invalid_params", error.Code);
        }

        [Theory]
        [InlineData(2000, 1000, 1000, 500)]
        [InlineData(5000, 1, 320, 1)]
        [InlineData(100000, 3, 320, 1)]
        public void ScaledHeightKeepsTheRatioAndIsNeverZero(int width, int height, int scaledWidth, int expected) {
            Assert.Equal(expected, AgentSelectors.ScaledHeight(width, height, scaledWidth));
        }
    }
}
